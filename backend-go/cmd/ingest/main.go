// Command ingest loads processed GeoJSON + CSV from data/processed into
// Supabase. Run after any Python pipeline change.
//
//	go run ./cmd/ingest -input ../data/processed -year 2026
package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/joho/godotenv"
)

func main() {
	_ = godotenv.Load("../.env")

	in := flag.String("input", "../data/processed", "processed outputs dir")
	year := flag.Int("year", 0, "year to ingest (0 = all)")
	flag.Parse()

	ctx := context.Background()
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		log.Fatal("DATABASE_URL not set")
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		log.Fatalf("pgx: %v", err)
	}
	defer pool.Close()

	// 1) district monthly series -> monthly_index
	if err := ingestMonthlyCSV(ctx, pool,
		filepath.Join(*in, "csv", "SPI_Latur_district_monthly.csv"),
		[]string{"SPI1", "SPI3", "SPI6", "SPI12"}, *year); err != nil {
		log.Fatalf("spi csv: %v", err)
	}
	if err := ingestMonthlyCSV(ctx, pool,
		filepath.Join(*in, "csv", "sentinel_Latur_district_monthly.csv"),
		[]string{"NDVI", "EVI", "NDMI", "VCI", "VHI"}, *year); err != nil {
		log.Fatalf("sentinel csv: %v", err)
	}
	if err := ingestMonthlyCSV(ctx, pool,
		filepath.Join(*in, "csv", "CDI_Latur_district_monthly.csv"),
		[]string{"CDI"}, *year); err != nil {
		log.Fatalf("cdi csv: %v", err)
	}

	// 2) per-pixel GeoJSON per index per year -> pixel_index
	for _, ind := range []string{"spi1", "spi3", "spi6", "spi12",
		"ndvi", "evi", "ndmi", "vci", "vhi", "cdi"} {
		dir := filepath.Join(*in, ind)
		files, _ := filepath.Glob(filepath.Join(dir, "*.geojson"))
		for _, f := range files {
			y := yearFromName(f)
			if *year != 0 && y != *year {
				continue
			}
			if err := ingestPixelGeoJSON(ctx, pool, ind, y, f); err != nil {
				log.Printf("  warn: %s: %v", f, err)
			}
		}
	}
	fmt.Println("ingest complete.")
}

// --- monthly ---------------------------------------------------------

func ingestMonthlyCSV(ctx context.Context, pool *pgxpool.Pool,
	path string, columns []string, yearFilter int) error {

	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	rdr := csv.NewReader(f)
	rows, err := rdr.ReadAll()
	if err != nil {
		return err
	}
	if len(rows) < 2 {
		return nil
	}
	head := map[string]int{}
	for i, h := range rows[0] {
		head[h] = i
	}

	tx, err := pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	for _, r := range rows[1:] {
		y, _ := strconv.Atoi(r[head["year"]])
		if yearFilter != 0 && y != yearFilter {
			continue
		}
		m, _ := strconv.Atoi(r[head["month"]])
		for _, col := range columns {
			if _, ok := head[col]; !ok {
				continue
			}
			val, err := parseFloat(r[head[col]])
			if err != nil {
				continue
			}
			classCol := col + "_class"
			class := ""
			if idx, ok := head[classCol]; ok {
				class = r[idx]
			}
			pct, _ := parseFloat(valueOr(r, head, col+"_pct_area_dry"))

			_, err = tx.Exec(ctx, `
				insert into monthly_index (index_name, year, month, value, class_label, pct_area_dry)
				values ($1, $2, $3, $4, $5, $6)
				on conflict (index_name, year, month)
				do update set value = excluded.value,
				              class_label = excluded.class_label,
				              pct_area_dry = excluded.pct_area_dry
			`, strings.ToLower(col), y, m, val, class, pct)
			if err != nil {
				return err
			}
		}
	}
	return tx.Commit(ctx)
}

// --- pixel GeoJSON ---------------------------------------------------

func ingestPixelGeoJSON(ctx context.Context, pool *pgxpool.Pool,
	index string, year int, path string) error {

	b, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	var fc struct {
		Features []struct {
			Properties map[string]any `json:"properties"`
			Geometry   json.RawMessage `json:"geometry"`
			ID         int             `json:"id"`
		} `json:"features"`
	}
	if err := json.Unmarshal(b, &fc); err != nil {
		return err
	}

	tx, err := pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	// delete existing year's rows for this index (idempotent reload)
	if _, err := tx.Exec(ctx,
		`delete from pixel_index where index_name = $1 and year = $2`,
		index, year); err != nil {
		return err
	}

	for _, feat := range fc.Features {
		props := feat.Properties
		lon, _ := props["lon"].(float64)
		lat, _ := props["lat"].(float64)
		for m := 1; m <= 12; m++ {
			col := fmt.Sprintf("M%02d", m)
			raw, ok := props[col]
			if !ok || raw == nil {
				continue
			}
			val, ok := raw.(float64)
			if !ok {
				continue
			}
			_, err := tx.Exec(ctx, `
				insert into pixel_index (index_name, year, month, pixel_id, lon, lat, value, geom)
				values ($1, $2, $3, $4, $5, $6, $7,
				        ST_SetSRID(ST_GeomFromGeoJSON($8), 4326))
			`, index, year, m, feat.ID, lon, lat, val, string(feat.Geometry))
			if err != nil {
				return err
			}
		}
	}
	fmt.Printf("  ingested %-5s %d  (%d features)\n", index, year, len(fc.Features))
	return tx.Commit(ctx)
}

// --- helpers ---------------------------------------------------------

func parseFloat(s string) (float64, error) {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "nan") {
		return 0, fmt.Errorf("empty")
	}
	return strconv.ParseFloat(s, 64)
}

func valueOr(row []string, head map[string]int, col string) string {
	if idx, ok := head[col]; ok {
		return row[idx]
	}
	return ""
}

func yearFromName(path string) int {
	base := strings.TrimSuffix(filepath.Base(path), ".geojson")
	parts := strings.Split(base, "_")
	for i := len(parts) - 1; i >= 0; i-- {
		if y, err := strconv.Atoi(parts[i]); err == nil && y > 1900 && y < 2100 {
			return y
		}
	}
	return 0
}
