# Public Assets

Static files copied verbatim into the build output: `favicon.svg`, `robots.txt`, and any
images referenced by absolute path.

Keep this small — everything here is served uncached-by-default from CloudFront. Assets
imported from `src/` get content-hashed filenames and cache far better; prefer that.
