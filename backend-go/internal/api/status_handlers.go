package api

import (
	"net/http"
	"strings"

	"github.com/latur-drought/backend-go/internal/status"
)

// --- Dashboard header -------------------------------------------------

func (s *Server) handleLatestStatus(w http.ResponseWriter, r *http.Request) {
	data, err := status.ReadLatest()
	if err != nil {
		writeErr(w, http.StatusServiceUnavailable, "STATUS_UNAVAILABLE",
			"latest_status.json not available yet")
		return
	}
	writeJSON(w, http.StatusOK, data)
}

func (s *Server) handleDataAvailability(w http.ResponseWriter, r *http.Request) {
	data, err := status.ReadAvailability()
	if err != nil {
		writeErr(w, http.StatusServiceUnavailable, "AVAIL_UNAVAILABLE",
			"data_availability.json not available yet")
		return
	}
	writeJSON(w, http.StatusOK, data)
}

// --- Master table + derived ------------------------------------------

func (s *Server) handleMaster(w http.ResponseWriter, r *http.Request) {
	rows, err := status.ReadMaster()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "MASTER_READ", err.Error())
		return
	}
	tehsil := strings.TrimSpace(r.URL.Query().Get("tehsil"))
	village := strings.TrimSpace(r.URL.Query().Get("village"))
	from := r.URL.Query().Get("from")
	to := r.URL.Query().Get("to")
	filtered := make([]status.MasterRow, 0, len(rows))
	for _, m := range rows {
		if tehsil != "" && !strings.EqualFold(m["tehsil"], tehsil) {
			continue
		}
		if village != "" && !strings.EqualFold(m["village"], village) {
			continue
		}
		p := m["observation_period"]
		if from != "" && p < from {
			continue
		}
		if to != "" && p > to {
			continue
		}
		filtered = append(filtered, m)
	}
	writeJSON(w, http.StatusOK, filtered)
}

// GET /api/v1/latest?tehsil=Latur&village=
//
// Returns the most recent validated row for a tehsil (or Latur district
// if omitted). Fields that are missing come back as empty strings so the
// frontend can render them as "unavailable" rather than zero.
func (s *Server) handleLatest(w http.ResponseWriter, r *http.Request) {
	rows, err := status.ReadMaster()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "MASTER_READ", err.Error())
		return
	}
	tehsil := strings.TrimSpace(r.URL.Query().Get("tehsil"))
	village := strings.TrimSpace(r.URL.Query().Get("village"))
	if tehsil == "" {
		tehsil = "Latur"
	}
	subset := make([]status.MasterRow, 0)
	for _, m := range rows {
		if !strings.EqualFold(m["tehsil"], tehsil) {
			continue
		}
		if village != "" && !strings.EqualFold(m["village"], village) {
			continue
		}
		if village == "" && m["village"] != "" {
			continue   // tehsil-level view: only pick tehsil rows
		}
		subset = append(subset, m)
	}
	latest := status.Latest(subset)
	if latest == nil {
		writeErr(w, http.StatusNotFound, "NO_DATA",
			"no master rows for "+tehsil+" / "+village)
		return
	}
	writeJSON(w, http.StatusOK, latest)
}

// GET /api/v1/compare?index=cdi&a=2024-05&b=2026-05
//
// Returns the two periods side by side (per-tehsil) so the slider widget
// can draw them without a second round-trip.
func (s *Server) handleCompare(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	a, b := q.Get("a"), q.Get("b")
	if a == "" || b == "" {
		writeErr(w, http.StatusBadRequest, "BAD_INPUT", "a and b are required (YYYY-MM)")
		return
	}
	rows, err := status.ReadMaster()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "MASTER_READ", err.Error())
		return
	}
	A, B := []status.MasterRow{}, []status.MasterRow{}
	for _, m := range rows {
		switch m["observation_period"] {
		case a:
			A = append(A, m)
		case b:
			B = append(B, m)
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"a": map[string]any{"period": a, "rows": A},
		"b": map[string]any{"period": b, "rows": B},
	})
}

// GET /api/v1/animation?index=cdi&from=2016-01&to=2026-10
//
// Returns an ordered array of {period, geojson_url} so the player can
// prefetch frames. Pixel GeoJSON remains at /api/v1/indices/:name/:y/:m.
func (s *Server) handleAnimation(w http.ResponseWriter, r *http.Request) {
	name := strings.ToLower(r.URL.Query().Get("index"))
	if !validIndices[name] {
		writeErr(w, http.StatusBadRequest, "BAD_INDEX", "unknown index: "+name)
		return
	}
	avail, err := status.ReadAvailability()
	if err != nil {
		writeErr(w, http.StatusServiceUnavailable, "AVAIL_UNAVAILABLE", "no availability data")
		return
	}
	// For NDVI/EVI/VHI we use the sentinel manifest; for SPI/PCI we use chirps.
	key := "sentinel2"
	if strings.HasPrefix(name, "spi") || name == "pci" {
		key = "chirps"
	}
	src, _ := avail[key].(map[string]any)
	periods, _ := src["periods"].([]any)
	from := r.URL.Query().Get("from")
	to := r.URL.Query().Get("to")
	frames := []map[string]string{}
	for _, p := range periods {
		ps, _ := p.(string)
		if from != "" && ps < from {
			continue
		}
		if to != "" && ps > to {
			continue
		}
		parts := strings.Split(ps, "-")
		if len(parts) != 2 {
			continue
		}
		frames = append(frames, map[string]string{
			"period":       ps,
			"geojson_url":  "/api/v1/indices/" + name + "/" + parts[0] + "/" + parts[1],
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"index": name, "count": len(frames), "frames": frames,
	})
}
