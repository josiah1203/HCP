{{- define "hcp-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "hcp-platform.namespace" -}}
{{- .Values.global.namespace | default "hcp" }}
{{- end }}

{{- define "hcp-platform.postgresHost" -}}
{{- .Values.postgresql.fullnameOverride | default (printf "%s-postgresql" .Release.Name) }}
{{- end }}

{{- define "hcp-platform.redisHost" -}}
{{- printf "%s-master" (.Values.redis.fullnameOverride | default (printf "%s-redis" .Release.Name)) }}
{{- end }}

{{- define "hcp-platform.minioHost" -}}
{{- .Values.minio.fullnameOverride | default (printf "%s-minio" .Release.Name) }}
{{- end }}

{{- define "hcp-platform.databaseUrl" -}}
{{- $user := .Values.secrets.postgresUser -}}
{{- $pass := .Values.secrets.postgresPassword -}}
{{- $db := .Values.secrets.postgresDatabase -}}
{{- $host := include "hcp-platform.postgresHost" . -}}
{{- $ns := include "hcp-platform.namespace" . -}}
{{- printf "postgresql+psycopg2://%s:%s@%s.%s.svc.cluster.local:5432/%s" $user $pass $host $ns $db }}
{{- end }}

{{- define "hcp-platform.redisUrl" -}}
{{- $host := include "hcp-platform.redisHost" . -}}
{{- $ns := include "hcp-platform.namespace" . -}}
{{- printf "redis://%s.%s.svc.cluster.local:6379/0" $host $ns }}
{{- end }}

{{- define "hcp-platform.minioEndpoint" -}}
{{- $host := include "hcp-platform.minioHost" . -}}
{{- $ns := include "hcp-platform.namespace" . -}}
{{- printf "http://%s.%s.svc.cluster.local:9000" $host $ns }}
{{- end }}
