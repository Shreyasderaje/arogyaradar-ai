# Local Karnataka district boundary data

Place the approved boundary file at `public/data/karnataka-districts.geojson`.
Vite serves this file at `/data/karnataka-districts.geojson`.

The file must be a GeoJSON `FeatureCollection`. Each feature must have a
`Polygon` or `MultiPolygon` geometry with valid WGS84 longitude/latitude
coordinates and a `properties` object containing at least one of these string
properties:

- `district_id`: matches an existing district `id` in `src/data/demoData.js`
- `district_name`: matches an existing district `name` in `src/data/demoData.js`
- `DISTRICT`: supported source column, including historical aliases for
  Bangalore/Bengaluru Urban, Belgaum/Belagavi, Gulbarga/Kalaburagi, and
  Mysore/Mysuru.

Matching is case-insensitive and treats spaces and underscores as hyphens. Vite
serves the public file from `/data/karnataka-districts.geojson`.
Current demo records include `bengaluru-urban`, `mysuru`,
`dakshina-kannada`, `kalaburagi`, and `belagavi`. Other valid Karnataka district
features may also be included; they render without a synthetic score until a
matching demo record exists.

Do not add invented coordinates. Preserve the boundary provider's source and
license attribution with the data when one is supplied.
