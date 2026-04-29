# abstract: Production nginx gateway image with repository-owned route configuration.
# out_of_scope: TLS certificate termination and application service runtimes.
FROM nginx:1.29-bookworm

COPY infra/docker/nginx/default.conf /etc/nginx/conf.d/default.conf
