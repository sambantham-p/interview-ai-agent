// Mirrors backend/app/schemas/response.py and the payload shapes each
// route's `data` field actually carries — kept in sync by hand for now;
// revisit once the backend exposes an OpenAPI-generated client instead.

export interface HealthCheck {
  service: string
  health: string
}
