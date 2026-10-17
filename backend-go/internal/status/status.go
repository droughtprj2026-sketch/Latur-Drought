// Package status reads the dashboard-ready status / master files that
// scripts/dashboard_master.py writes under outputs/Dashboard/.
package status

import (
	"encoding/csv"
	"encoding/json"
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

var defaultDir = "../outputs/Dashboard"

// Dir returns the dashboard outputs directory, honoring $DASHBOARD_DIR.
func Dir() string {
	if v := os.Getenv("DASHBOARD_DIR"); v != "" {
		return v
	}
	return defaultDir
}

// LatestStatus mirrors outputs/Dashboard/latest_status.json.
type LatestStatus struct {
	GeneratedAt      string                 `json:"generated_at"`
	MonitoringStatus string                 `json:"monitoring_status"`
	Sentinel2        map[string]any         `json:"sentinel2"`
	Chirps           map[string]any         `json:"chirps"`
	Composite        map[string]any         `json:"composite"`
	Region           map[string]any         `json:"region"`
}

// MasterRow is one row of drought_monitoring_master.csv (strings only; the
// frontend parses numbers to preserve empty cells as "unavailable" rather
// than zero).
type MasterRow map[string]string

type cache struct {
	mu          sync.RWMutex
	status      *LatestStatus
	statusAt    time.Time
	master      []MasterRow
	masterAt    time.Time
	avail       map[string]any
	availAt     time.Time
}

var cc = &cache{}

const ttl = 30 * time.Second

func ReadLatest() (*LatestStatus, error) {
	cc.mu.RLock()
	if cc.status != nil && time.Since(cc.statusAt) < ttl {
		s := cc.status
		cc.mu.RUnlock()
		return s, nil
	}
	cc.mu.RUnlock()
	b, err := os.ReadFile(filepath.Join(Dir(), "latest_status.json"))
	if err != nil {
		return nil, err
	}
	var s LatestStatus
	if err := json.Unmarshal(b, &s); err != nil {
		return nil, err
	}
	cc.mu.Lock()
	cc.status, cc.statusAt = &s, time.Now()
	cc.mu.Unlock()
	return &s, nil
}

func ReadAvailability() (map[string]any, error) {
	cc.mu.RLock()
	if cc.avail != nil && time.Since(cc.availAt) < ttl {
		m := cc.avail
		cc.mu.RUnlock()
		return m, nil
	}
	cc.mu.RUnlock()
	b, err := os.ReadFile(filepath.Join(Dir(), "data_availability.json"))
	if err != nil {
		return nil, err
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	cc.mu.Lock()
	cc.avail, cc.availAt = m, time.Now()
	cc.mu.Unlock()
	return m, nil
}

// ReadMaster parses the master CSV. Returns all rows; filter in the caller.
func ReadMaster() ([]MasterRow, error) {
	cc.mu.RLock()
	if cc.master != nil && time.Since(cc.masterAt) < ttl {
		rows := cc.master
		cc.mu.RUnlock()
		return rows, nil
	}
	cc.mu.RUnlock()
	f, err := os.Open(filepath.Join(Dir(), "drought_monitoring_master.csv"))
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return []MasterRow{}, nil
		}
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	raw, err := r.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(raw) < 2 {
		return []MasterRow{}, nil
	}
	head := raw[0]
	out := make([]MasterRow, 0, len(raw)-1)
	for _, row := range raw[1:] {
		m := MasterRow{}
		for i, col := range head {
			if i < len(row) {
				m[col] = strings.TrimSpace(row[i])
			}
		}
		out = append(out, m)
	}
	cc.mu.Lock()
	cc.master, cc.masterAt = out, time.Now()
	cc.mu.Unlock()
	return out, nil
}

// Latest returns the most recent period where RF status == success, or
// the last period with any data if none validated.
func Latest(rows []MasterRow) MasterRow {
	var best MasterRow
	var bestPeriod string
	for _, r := range rows {
		if r["data_quality_status"] == "success" && r["observation_period"] > bestPeriod {
			best = r
			bestPeriod = r["observation_period"]
		}
	}
	if best == nil && len(rows) > 0 {
		best = rows[len(rows)-1]
	}
	return best
}

// Float parses a master-table cell as float. Empty string → (0, false)
// so the caller can decide to render it as "unavailable", NEVER as zero.
func Float(r MasterRow, key string) (float64, bool) {
	v := strings.TrimSpace(r[key])
	if v == "" {
		return 0, false
	}
	f, err := strconv.ParseFloat(v, 64)
	if err != nil {
		return 0, false
	}
	return f, true
}
