package api

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/go-chi/chi/v5"
)

var validIndices = map[string]bool{
	"spi1": true, "spi3": true, "spi6": true, "spi12": true,
	"ndvi": true, "evi": true, "pci": true, "vhi": true, "cdi": true,
}

type apiError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

func writeErr(w http.ResponseWriter, status int, code, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]apiError{"error": {Code: code, Message: msg}})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// --- handlers --------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleManifest(w http.ResponseWriter, r *http.Request) {
	m, err := s.Store.Manifest(r.Context())
	if err != nil {
		s.Logger.Error("manifest query failed", "err", err)
		writeErr(w, http.StatusInternalServerError, "INTERNAL", "manifest unavailable")
		return
	}
	writeJSON(w, http.StatusOK, m)
}

func (s *Server) handleTehsils(w http.ResponseWriter, r *http.Request) {
	fc, err := s.Store.TehsilGeoJSON(r.Context())
	if err != nil {
		s.Logger.Error("tehsils query failed", "err", err)
		writeErr(w, http.StatusInternalServerError, "INTERNAL", "tehsils unavailable")
		return
	}
	w.Header().Set("Content-Type", "application/geo+json")
	_, _ = w.Write(fc)
}

func (s *Server) handleIndexGeoJSON(w http.ResponseWriter, r *http.Request) {
	name := strings.ToLower(chi.URLParam(r, "name"))
	if !validIndices[name] {
		writeErr(w, http.StatusBadRequest, "BAD_INDEX", "unknown index: "+name)
		return
	}
	year, err := strconv.Atoi(chi.URLParam(r, "year"))
	if err != nil || year < 1900 || year > 2100 {
		writeErr(w, http.StatusBadRequest, "BAD_YEAR", "year must be 1900..2100")
		return
	}
	month, err := strconv.Atoi(chi.URLParam(r, "month"))
	if err != nil || month < 1 || month > 12 {
		writeErr(w, http.StatusBadRequest, "BAD_MONTH", "month must be 1..12")
		return
	}
	fc, err := s.Store.IndexGeoJSON(r.Context(), name, year, month)
	if err != nil {
		s.Logger.Error("index geojson query failed", "err", err, "name", name, "year", year, "month", month)
		writeErr(w, http.StatusInternalServerError, "INTERNAL", "query failed")
		return
	}
	if fc == nil {
		writeErr(w, http.StatusNotFound, "NOT_FOUND", "no data for "+name+" "+chi.URLParam(r, "year")+"-"+chi.URLParam(r, "month"))
		return
	}
	w.Header().Set("Content-Type", "application/geo+json")
	w.Header().Set("Cache-Control", "public, max-age=86400")
	_, _ = w.Write(fc)
}

func (s *Server) handleTimeseries(w http.ResponseWriter, r *http.Request) {
	name := strings.ToLower(chi.URLParam(r, "name"))
	if !validIndices[name] {
		writeErr(w, http.StatusBadRequest, "BAD_INDEX", "unknown index: "+name)
		return
	}
	from := r.URL.Query().Get("from")
	to := r.URL.Query().Get("to")
	points, err := s.Store.Timeseries(r.Context(), name, from, to)
	if err != nil {
		s.Logger.Error("timeseries query failed", "err", err)
		writeErr(w, http.StatusInternalServerError, "INTERNAL", "query failed")
		return
	}
	writeJSON(w, http.StatusOK, points)
}

func (s *Server) handleCDI(w http.ResponseWriter, r *http.Request) {
	year, err := strconv.Atoi(chi.URLParam(r, "year"))
	if err != nil {
		writeErr(w, http.StatusBadRequest, "BAD_YEAR", "year must be an int")
		return
	}
	month, err := strconv.Atoi(chi.URLParam(r, "month"))
	if err != nil || month < 1 || month > 12 {
		writeErr(w, http.StatusBadRequest, "BAD_MONTH", "month must be 1..12")
		return
	}
	payload, err := s.Store.CDISummary(r.Context(), year, month)
	if err != nil {
		s.Logger.Error("cdi summary failed", "err", err)
		writeErr(w, http.StatusInternalServerError, "INTERNAL", "query failed")
		return
	}
	writeJSON(w, http.StatusOK, payload)
}

func (s *Server) handleIngest(w http.ResponseWriter, r *http.Request) {
	// Ingest is a long-running job; for now we accept-and-dispatch.
	s.Logger.Info("admin ingest requested")
	writeJSON(w, http.StatusAccepted, map[string]string{"status": "accepted"})
}
