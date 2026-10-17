// Package db wraps every Postgres query the API uses.
// Queries lean on PostGIS to assemble GeoJSON on the database side (ST_AsGeoJSON)
// so the Go process never has to shuffle large polygon arrays through memory.
package db

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type Store struct {
	pool *pgxpool.Pool
}

func New(pool *pgxpool.Pool) *Store {
	return &Store{pool: pool}
}

// --- types -----------------------------------------------------------

type Manifest struct {
	District string              `json:"district"`
	Years    []int               `json:"years"`
	Indices  map[string]IndexMan `json:"indices"`
	AsOf     time.Time           `json:"as_of"`
}

type IndexMan struct {
	Source string `json:"source"`
	Unit   string `json:"unit"`
	Years  []int  `json:"years"`
}

type TimeseriesPoint struct {
	Date       string   `json:"date"`
	Value      *float64 `json:"value"`
	Class      string   `json:"class"`
	PctAreaDry *float64 `json:"pct_area_dry,omitempty"`
}

type CDISummary struct {
	Year    int                `json:"year"`
	Month   int                `json:"month"`
	Mean    *float64           `json:"mean"`
	Class   string             `json:"class"`
	Tehsils []TehsilCDI        `json:"tehsils"`
	GeoJSON json.RawMessage    `json:"geojson"`
	Meta    map[string]float64 `json:"weights"`
}

type TehsilCDI struct {
	Name  string  `json:"name"`
	Mean  float64 `json:"mean"`
	Class string  `json:"class"`
}

// --- queries ---------------------------------------------------------

func (s *Store) Manifest(ctx context.Context) (*Manifest, error) {
	m := &Manifest{
		District: "Latur",
		Indices:  map[string]IndexMan{},
		AsOf:     time.Now().UTC(),
	}
	// Years available: distinct from monthly_index.
	rows, err := s.pool.Query(ctx, `
		select distinct year from monthly_index order by year
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var y int
		if err := rows.Scan(&y); err != nil {
			return nil, err
		}
		m.Years = append(m.Years, y)
	}

	// Per-index year coverage.
	idxRows, err := s.pool.Query(ctx, `
		select index_name, array_agg(distinct year order by year) as years
		from monthly_index group by index_name
	`)
	if err != nil {
		return nil, err
	}
	defer idxRows.Close()
	for idxRows.Next() {
		var name string
		var years []int
		if err := idxRows.Scan(&name, &years); err != nil {
			return nil, err
		}
		m.Indices[name] = IndexMan{Source: sourceFor(name), Unit: unitFor(name), Years: years}
	}
	return m, nil
}

func (s *Store) TehsilGeoJSON(ctx context.Context) ([]byte, error) {
	const q = `
		select json_build_object(
			'type', 'FeatureCollection',
			'features', coalesce(json_agg(
				json_build_object(
					'type', 'Feature',
					'id', id,
					'properties', json_build_object('name', name),
					'geometry', ST_AsGeoJSON(geom)::json
				)
			), '[]'::json)
		)::text
		from tehsils
	`
	var out []byte
	if err := s.pool.QueryRow(ctx, q).Scan(&out); err != nil {
		return nil, err
	}
	return out, nil
}

func (s *Store) IndexGeoJSON(ctx context.Context, index string, year, month int) ([]byte, error) {
	const q = `
		select json_build_object(
			'type', 'FeatureCollection',
			'features', coalesce(json_agg(
				json_build_object(
					'type', 'Feature',
					'id', pixel_id,
					'properties', json_build_object(
						'value', value,
						'lon', lon,
						'lat', lat
					),
					'geometry', ST_AsGeoJSON(geom)::json
				)
			), '[]'::json)
		)::text
		from pixel_index
		where index_name = $1 and year = $2 and month = $3
	`
	var out []byte
	err := s.pool.QueryRow(ctx, q, index, year, month).Scan(&out)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	return out, err
}

func (s *Store) Timeseries(ctx context.Context, index, from, to string) ([]TimeseriesPoint, error) {
	args := []any{index}
	q := `
		select
			to_char(make_date(year, month, 1), 'YYYY-MM') as date,
			value, coalesce(class_label, 'No data'), pct_area_dry
		from monthly_index
		where index_name = $1
	`
	if from != "" {
		args = append(args, from)
		q += ` and to_char(make_date(year, month, 1), 'YYYY-MM') >= $` + itoa(len(args))
	}
	if to != "" {
		args = append(args, to)
		q += ` and to_char(make_date(year, month, 1), 'YYYY-MM') <= $` + itoa(len(args))
	}
	q += ` order by year, month`

	rows, err := s.pool.Query(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []TimeseriesPoint
	for rows.Next() {
		var p TimeseriesPoint
		if err := rows.Scan(&p.Date, &p.Value, &p.Class, &p.PctAreaDry); err != nil {
			return nil, err
		}
		out = append(out, p)
	}
	return out, nil
}

func (s *Store) CDISummary(ctx context.Context, year, month int) (*CDISummary, error) {
	summary := &CDISummary{Year: year, Month: month}

	// District-mean + class.
	err := s.pool.QueryRow(ctx, `
		select value, coalesce(class_label, 'No data')
		from monthly_index
		where index_name = 'cdi' and year = $1 and month = $2
	`, year, month).Scan(&summary.Mean, &summary.Class)
	if err != nil && !errors.Is(err, pgx.ErrNoRows) {
		return nil, err
	}

	// Per-tehsil zonal means (PostGIS does the heavy lifting).
	rows, err := s.pool.Query(ctx, `
		select t.name,
		       avg(p.value)::float as mean
		from tehsils t
		join pixel_index p
		     on p.index_name = 'cdi' and p.year = $1 and p.month = $2
		    and ST_Intersects(t.geom, p.geom)
		group by t.name
		order by mean
	`, year, month)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var t TehsilCDI
		if err := rows.Scan(&t.Name, &t.Mean); err != nil {
			return nil, err
		}
		t.Class = classifyCDI(t.Mean)
		summary.Tehsils = append(summary.Tehsils, t)
	}

	// Pixel GeoJSON (reuse IndexGeoJSON).
	gj, err := s.IndexGeoJSON(ctx, "cdi", year, month)
	if err == nil {
		summary.GeoJSON = gj
	}
	return summary, nil
}

// --- helpers ---------------------------------------------------------

func sourceFor(name string) string {
	switch name {
	case "spi1", "spi3", "spi6", "spi12":
		return "CHIRPS v2.0"
	case "ndvi", "evi", "ndmi", "vci", "vhi":
		return "Sentinel-2 L2A"
	case "pci":
		return "CHIRPS (normalized)"
	case "cdi":
		return "composite"
	}
	return "unknown"
}

func unitFor(name string) string {
	switch name {
	case "ndvi", "evi", "ndmi":
		return "0..1"
	case "vci", "vhi":
		return "%"
	}
	return "z"
}

// classifyCDI maps a composite drought score (0..1 drought intensity) to
// the D-class scale. Thresholds match config/composite.yaml.
func classifyCDI(v float64) string {
	switch {
	case v < 0.20:
		return "None"
	case v < 0.35:
		return "D0"
	case v < 0.50:
		return "D1"
	case v < 0.65:
		return "D2"
	case v < 0.80:
		return "D3"
	default:
		return "D4"
	}
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	negative := n < 0
	if negative {
		n = -n
	}
	buf := [20]byte{}
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if negative {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
