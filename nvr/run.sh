#!/usr/bin/with-contenv bashio

bashio::log.info "Starting NVR Stream add-on..."

NVR_HOST=$(bashio::config 'nvr_host')
NVR_PORT=$(bashio::config 'nvr_port')
NVR_USER=$(bashio::config 'nvr_user')
NVR_PASS=$(bashio::config 'nvr_pass')
CHANNELS=$(bashio::config 'channels')
STREAMS=$(bashio::config 'streams')

# Pass credentials to connect.py via the environment only, so they never
# appear in the go2rtc exec URL, generated config, logs, or ps output.
export NVR_HOST NVR_PORT NVR_USER NVR_PASS CHANNELS STREAMS

# Watchdog: restarts go2rtc if a configured stream stops serving frames.
python3 /app/watchdog.py &

# Generate go2rtc.yaml
cat > /tmp/go2rtc.yaml <<EOF
streams:
EOF

IFS=',' read -ra CH_LIST <<< "$CHANNELS"
IFS=',' read -ra ST_LIST <<< "$STREAMS"

for ch in "${CH_LIST[@]}"; do
  ch=$(echo $ch | tr -d ' ')
  for st in "${ST_LIST[@]}"; do
    st=$(echo $st | tr -d ' ')
    NAME="cam${ch}_${st}"
    CMD="python3 /app/connect.py -c ${ch} -s ${st}"
    CMD="${CMD} --nvr-host ${NVR_HOST}"
    CMD="${CMD} --nvr-port ${NVR_PORT}"
    CMD="${CMD} --nvr-user ${NVR_USER}"
    bashio::log.info "  Stream: ${NAME}"
    cat >> /tmp/go2rtc.yaml <<EOF
  ${NAME}: exec:${CMD}#killsignal=15
EOF
  done
done

bashio::log.info "Generated go2rtc.yaml:"
cat /tmp/go2rtc.yaml

exec /usr/local/bin/go2rtc -config /tmp/go2rtc.yaml
