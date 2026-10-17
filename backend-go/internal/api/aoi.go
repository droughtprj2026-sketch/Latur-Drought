package api

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// MaxAOIBytes is the hard cap for an uploaded shapefile / GeoJSON.
const MaxAOIBytes = 20 * 1024 * 1024 // 20 MB

// POST /api/v1/admin/aoi
//
// Accepts a GeoJSON FeatureCollection in the request body (one AOI, usually
// Latur district or a tehsil overlay), writes it to data/vector/, and
// enqueues a run of scripts/pipeline_gee.py against it.
//
// Response: 202 Accepted  + a job id the frontend can poll.
func (s *Server) handleUploadAOI(w http.ResponseWriter, r *http.Request) {
	ct := r.Header.Get("Content-Type")
	if !strings.HasPrefix(ct, "application/geo+json") &&
		!strings.HasPrefix(ct, "application/json") {
		writeErr(w, http.StatusUnsupportedMediaType, "BAD_CT",
			"send application/geo+json or application/json")
		return
	}

	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, MaxAOIBytes))
	if err != nil {
		writeErr(w, http.StatusRequestEntityTooLarge, "TOO_LARGE",
			fmt.Sprintf("AOI must be <= %d bytes", MaxAOIBytes))
		return
	}
	// Validate it is at least parseable GeoJSON.
	var probe struct {
		Type     string `json:"type"`
		Features []any  `json:"features"`
	}
	if err := json.Unmarshal(body, &probe); err != nil || probe.Type == "" {
		writeErr(w, http.StatusBadRequest, "BAD_GEOJSON", "not valid GeoJSON")
		return
	}
	if probe.Type == "FeatureCollection" && len(probe.Features) == 0 {
		writeErr(w, http.StatusBadRequest, "EMPTY", "FeatureCollection has no features")
		return
	}

	// Write it where the Python pipeline will find it.
	vectorDir := getenv("VECTOR_DIR", "../data/vector")
	if err := os.MkdirAll(vectorDir, 0o755); err != nil {
		writeErr(w, http.StatusInternalServerError, "FS", "cannot create vector dir")
		return
	}
	name := fmt.Sprintf("aoi_%d.geojson", time.Now().UnixNano())
	outPath := filepath.Join(vectorDir, name)
	if err := os.WriteFile(outPath, body, 0o644); err != nil {
		writeErr(w, http.StatusInternalServerError, "FS", "cannot write AOI")
		return
	}

	// Fire-and-forget the Python pipeline. In production this becomes a
	// task queue (Supabase edge function, GitHub Actions dispatch, or a
	// Fly.io machine). For local dev, exec is fine.
	jobID := fmt.Sprintf("job_%d", time.Now().UnixNano())
	go func(path, id string) {
		pythonBin := getenv("PYTHON_BIN", "python3")
		script := getenv("PIPELINE_SCRIPT", "../scripts/pipeline_gee.py")
		cmd := exec.Command(pythonBin, script, "--aoi", path)
		cmd.Env = append(os.Environ(), "JOB_ID="+id)
		out, err := cmd.CombinedOutput()
		if err != nil {
			s.Logger.Error("pipeline failed", "job", id, "err", err,
				"stderr", string(out))
			return
		}
		s.Logger.Info("pipeline done", "job", id, "bytes", len(out))
	}(outPath, jobID)

	writeJSON(w, http.StatusAccepted, map[string]any{
		"job_id":   jobID,
		"aoi_file": name,
		"status":   "queued",
	})
}
