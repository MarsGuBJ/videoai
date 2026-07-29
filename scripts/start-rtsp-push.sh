#!/usr/bin/env bash
set -euo pipefail

RTSP_URL="${RTSP_URL:-rtsp://172.20.176.1:8554/cam}"
RTMP_URL="${RTMP_URL:-rtmp://127.0.0.1/live/cam}"
FFMPEG_BIN="${FFMPEG_BIN:-/usr/bin/ffmpeg}"
LOG_FILE="${LOG_FILE:-/tmp/videoai-cam-push.log}"
PID_FILE="${PID_FILE:-/tmp/videoai-cam-push.pid}"

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid="$(<"$PID_FILE")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

start() {
  if is_running; then
    echo "rtsp push already running: pid=$(<"$PID_FILE")"
    return 0
  fi

  rm -f "$PID_FILE"
  : >"$LOG_FILE"
  setsid bash -c '
    set -u
    pid_file="$1"
    log_file="$2"
    rtsp_url="$3"
    rtmp_url="$4"
    ffmpeg_bin="$5"
    child=""

    cleanup() {
      if [[ -n "$child" ]]; then
        kill "$child" 2>/dev/null || true
        wait "$child" 2>/dev/null || true
      fi
      rm -f "$pid_file"
      exit 0
    }

    echo "$$" >"$pid_file"
    trap cleanup TERM INT

    while true; do
      printf "%s starting ffmpeg: %s -> %s\n" "$(date -Is)" "$rtsp_url" "$rtmp_url" >>"$log_file"
      "$ffmpeg_bin" -hide_banner -loglevel warning -rtsp_transport tcp -i "$rtsp_url" -an -c:v copy -f flv "$rtmp_url" >>"$log_file" 2>&1 &
      child="$!"
      wait "$child" || true
      child=""
      printf "%s ffmpeg exited, reconnecting in 2s\n" "$(date -Is)" >>"$log_file"
      sleep 2
    done
  ' videoai-cam-push "$PID_FILE" "$LOG_FILE" "$RTSP_URL" "$RTMP_URL" "$FFMPEG_BIN" </dev/null >/dev/null 2>&1 &

  sleep 0.3
  if ! is_running; then
    echo "failed to start rtsp push" >&2
    tail -40 "$LOG_FILE" >&2 || true
    exit 1
  fi
  echo "rtsp push started: pid=$(<"$PID_FILE")"
}

stop() {
  if ! is_running; then
    rm -f "$PID_FILE"
    echo "rtsp push is not running"
    return 0
  fi

  local pid
  pid="$(<"$PID_FILE")"
  kill "$pid" 2>/dev/null || true
  for _ in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      echo "rtsp push stopped"
      return 0
    fi
    sleep 0.1
  done
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "rtsp push killed"
}

status() {
  if is_running; then
    echo "rtsp push running: pid=$(<"$PID_FILE")"
  else
    echo "rtsp push stopped"
    return 1
  fi
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  *)
    echo "usage: $0 [start|stop|restart|status]" >&2
    exit 2
    ;;
esac
