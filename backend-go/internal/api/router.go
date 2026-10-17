// Package api wires the HTTP routes for the Latur drought monitoring API.
package api

import (
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"

	"github.com/latur-drought/backend-go/internal/db"
)

// Server bundles the handler dependencies.
type Server struct {
	Store  *db.Store
	Logger *slog.Logger
}

// NewRouter returns an http.Handler with every /api/v1 route attached.
func NewRouter(store *db.Store, logger *slog.Logger) http.Handler {
	s := &Server{Store: store, Logger: logger}

	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Compress(5))
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(30 * time.Second))

	origins := strings.Split(getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:4000"), ",")
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   origins,
		AllowedMethods:   []string{"GET", "POST", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Content-Type", "Authorization"},
		AllowCredentials: false,
		MaxAge:           300,
	}))

	r.Route("/api/v1", func(r chi.Router) {
		r.Get("/health", s.handleHealth)
		r.Get("/manifest", s.handleManifest)
		r.Get("/tehsils", s.handleTehsils)
		r.Get("/indices/{name}/{year}/{month}", s.handleIndexGeoJSON)
		r.Get("/timeseries/{name}", s.handleTimeseries)
		r.Get("/cdi/{year}/{month}", s.handleCDI)

		// Dashboard-contract endpoints — read directly from the files
		// written by scripts/dashboard_master.py.
		r.Get("/status", s.handleLatestStatus)
		r.Get("/availability", s.handleDataAvailability)
		r.Get("/master", s.handleMaster)
		r.Get("/latest", s.handleLatest)
		r.Get("/compare", s.handleCompare)
		r.Get("/animation", s.handleAnimation)

		r.Route("/admin", func(r chi.Router) {
			r.Use(RequireServiceRole)
			r.Post("/ingest", s.handleIngest)
			r.Post("/aoi", s.handleUploadAOI)
		})
	})

	return r
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
