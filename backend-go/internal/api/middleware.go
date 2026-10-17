package api

import (
	"net/http"
	"os"
	"strings"
)

// RequireServiceRole gates admin endpoints behind the Supabase service-role
// JWT. The Node.js gateway is expected to attach the service_role key as a
// Bearer token on calls to /api/v1/admin/*.
func RequireServiceRole(next http.Handler) http.Handler {
	expected := os.Getenv("SUPABASE_SERVICE_ROLE_KEY")
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if expected == "" {
			writeErr(w, http.StatusServiceUnavailable, "NO_SERVICE_KEY",
				"server not configured for admin writes")
			return
		}
		auth := r.Header.Get("Authorization")
		token := strings.TrimPrefix(auth, "Bearer ")
		if token == "" || token != expected {
			writeErr(w, http.StatusUnauthorized, "UNAUTHORIZED", "admin token required")
			return
		}
		next.ServeHTTP(w, r)
	})
}
