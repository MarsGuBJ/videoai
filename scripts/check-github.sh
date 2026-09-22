#!/usr/bin/env bash
# GitHub 连通性体检脚本
#
# 背景：本机 github.com:443 被网络阻断（TCP 超时），但 SSH 通道
# (github.com:22 / ssh.github.com:443) 可用且主机密钥与 GitHub 官方一致。
# 另外 /etc/ssh 下有个错误属主的配置文件会让普通 ssh 命令直接失败。
#
# 用法：bash scripts/check-github.sh

set -uo pipefail

SSH_CONFIG="$HOME/.ssh/github.config"
REPO_CONF="$HOME/.ssh/github-repos.config"
KEY="$HOME/.ssh/id_ed25519_github"
TIMEOUT=8

GITHUB_ED25519="SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU"
GITHUB_RSA="SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s"

pass=0; fail=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

probe_tcp() { # host port -> 成功返回 0
  timeout "$TIMEOUT" bash -c "cat < /dev/null > /dev/tcp/$1/$2" 2>/dev/null
}

probe_tcp_n() { # host port 次数 -> 成功次数写入 PROBE_HITS
  local h="$1" p="$2" n="${3:-3}" hits=0 i
  for ((i = 1; i <= n; i++)); do probe_tcp "$h" "$p" && hits=$((hits + 1)); done
  PROBE_HITS="$hits/$n"
  [ "$hits" -eq "$n" ]
}

echo "════ GitHub 连通性体检 · $(date '+%F %T') ════"

echo
echo "[1/5] DNS 解析"
for h in github.com api.github.com codeload.github.com ssh.github.com; do
  ip=$(getent hosts "$h" 2>/dev/null | awk 'NR==1{print $1}')
  [ -n "$ip" ] && ok "$h -> $ip" || bad "$h 解析失败"
done

echo
echo "[2/5] TCP 端口可达性（每个探测 3 次，避免偶发 SYN-ACK 造成误判）"
for hp in github.com:443 github.com:22 ssh.github.com:443 codeload.github.com:443 raw.githubusercontent.com:443; do
  h=${hp%:*}; p=${hp#*:}
  if probe_tcp_n "$h" "$p" 3; then
    ok "$hp 可连通（3/3）"
  elif [ "${PROBE_HITS%/*}" -gt 0 ]; then
    # 本机实测过 github.com:443 间歇性只放通部分 SYN：TCP 偶尔通但 TLS 完不成。
    # 这类"假通"不能当作可用，故降级为 warn 并提示以 HTTPS 实测为准。
    warn "$hp 连接不稳定（$PROBE_HITS 次成功）—— 疑似间歇性阻断，以 HTTPS 实测为准"
  else
    bad "$hp 不可连通（0/3）"
  fi
done

echo
echo "[3/5] HTTPS 端点（用真实资源路径，非裸根路径）"
declare -A url_map=(
  ["api.github.com"]="https://api.github.com"
  ["codeload.github.com"]="https://codeload.github.com/octocat/Hello-World/tar.gz/refs/heads/master"
  ["raw.githubusercontent.com"]="https://raw.githubusercontent.com/git/git/master/README.md"
)
for name in api.github.com codeload.github.com raw.githubusercontent.com; do
  u="${url_map[$name]}"
  hits=0
  for _ in 1 2; do
    code=$(timeout $((TIMEOUT+4)) curl -sSL -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" "$u" 2>/dev/null)
    [ "$code" = "200" ] && hits=$((hits + 1))
  done
  # 本机实测存在选择性干扰：同一端点可能这次通、下次不通，故采样 2 次再判定
  if [ "$hits" -eq 2 ]; then ok "$name HTTP 200（2/2）"
  elif [ "$hits" -eq 1 ]; then warn "$name 不稳定（1/2）—— 该端点被间歇性干扰"
  else bad "$name 不可达（0/2）"; fi
done
# github.com 主站：HTTPS 克隆的关键端点
code=$(timeout $((TIMEOUT+4)) curl -sSL -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" https://github.com 2>/dev/null)
if [ "$code" = "200" ]; then
  ok "https://github.com HTTP 200（HTTPS 克隆可用）"
else
  bad "https://github.com 不可达（HTTP ${code:-超时}）—— HTTPS 克隆不可用，改用 SSH"
fi

# 真正有说服力的判据：实际跑一次 HTTPS ls-remote，而非只看端口/状态码
if GIT_CONFIG_GLOBAL=/dev/null timeout 30 git ls-remote https://github.com/octocat/Hello-World.git HEAD >/dev/null 2>&1; then
  ok "HTTPS git ls-remote 实测成功"
else
  bad "HTTPS git ls-remote 实测失败"
fi

echo
echo "[4/5] SSH 通道与主机密钥指纹核验"
if [ -f "$SSH_CONFIG" ]; then
  ks=$(mktemp); trap 'rm -f "$ks"' EXIT
  if timeout 12 ssh-keyscan -p 443 -t ed25519,rsa ssh.github.com >"$ks" 2>/dev/null; then
    fps=$(ssh-keygen -lf "$ks" 2>/dev/null | awk '{print $2}')
    if grep -qF "$GITHUB_ED25519" <<<"$fps" && grep -qF "$GITHUB_RSA" <<<"$fps"; then
      ok "ssh.github.com:443 主机密钥与 GitHub 官方一致（非中间人）"
    else
      bad "主机密钥与官方不符，疑似中间人！"; echo "$fps" | sed 's/^/      /'
    fi
  else
    bad "ssh.github.com:443 握手失败"
  fi
  # 本机 ssh 客户端是否受系统配置 bug 影响
  # 注意：必须先把输出存进变量再 grep —— 在 set -o pipefail 下，
  # `ssh ... | grep -q` 会因 grep -q 提前退出触发 SIGPIPE，把管道判成失败。
  sysmsg=$(ssh -o ConnectTimeout=3 -o BatchMode=yes -T git@github.com </dev/null 2>&1)
  if grep -q "Bad owner or permissions" <<<"$sysmsg"; then
    warn "普通 ssh 命令仍受 /etc/ssh 配置权限 bug 影响，须用 -F \$SSH_CONFIG 调用"
  else
    ok "系统 ssh 配置正常（可直接 ssh，无需 -F）"
  fi
else
  warn "未找到 $SSH_CONFIG（git 还未配置 SSH 通道）"
fi

echo
echo "[5/5] 认证状态"

# a) 仓库级 deploy key：逐个别名实测，这是最权威的判据
#    （账号级密钥未注册不影响它们，两者的用途不同）
if [ -f "$REPO_CONF" ]; then
  mapfile -t aliases < <(grep -oE '^Host[[:space:]]+github-[^[:space:]]+' "$REPO_CONF" | awk '{print $2}')
  if [ "${#aliases[@]}" -gt 0 ]; then
    echo "  -- 仓库级 Deploy Key --"
    for a in "${aliases[@]}"; do
      out=$(timeout 20 ssh -F "$SSH_CONFIG" -T -o ConnectTimeout=10 -o BatchMode=yes "git@$a" </dev/null 2>&1)
      who=$(grep -oE 'Hi [^!]+!' <<<"$out" | head -1)
      idf=$(ssh -G -F "$SSH_CONFIG" "$a" 2>/dev/null | awk '/^identityfile /{print $2}' | head -1)
      if [ -n "$who" ]; then
        ok "$a → $who（密钥 $(basename "${idf:-未知}")）"
      else
        bad "$a 认证失败：$(grep -oE 'Permission denied[^)]*|Could not resolve hostname[^ ]*' <<<"$out" | head -1)"
      fi
    done
  else
    warn "$REPO_CONF 存在但没有任何 Host 别名"
  fi
else
  warn "未配置仓库级 deploy key（$REPO_CONF 不存在）"
fi

# b) 默认 github.com 通道：按配置里 IdentityFile 的顺序逐把尝试
out=$(timeout 20 ssh -F "$SSH_CONFIG" -T -o ConnectTimeout=10 -o BatchMode=yes git@github.com </dev/null 2>&1)
who=$(grep -oE 'Hi [^!]+!' <<<"$out" | head -1)
if [ -n "$who" ]; then
  ok "github.com 通道认证成功：$who"
elif grep -qi "Permission denied" <<<"$out"; then
  warn "github.com 通道无可用钥匙（仅影响直接用 git@github.com: 的 URL）"
else
  bad "SSH 认证通道异常"; tail -2 <<<"$out" | sed 's/^/      /'
fi

# c) 账号级密钥仅作存在性提示，未注册不算体检失败
if [ -f "$KEY" ]; then
  echo "  （账号级密钥 $(ssh-keygen -lf "$KEY" 2>/dev/null | awk '{print $2}') 存在；如需访问任意仓库需注册到 GitHub 账号）"
fi

echo
echo "════ 汇总：$pass 项通过，$fail 项失败 ════"
[ "$fail" -eq 0 ] || exit 1
