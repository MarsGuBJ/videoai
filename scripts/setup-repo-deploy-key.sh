#!/usr/bin/env bash
# 为指定仓库配置「仅限该仓库」的访问权限（GitHub Deploy Key 方案）
#
# 原理：deploy key 是挂在**仓库**上而非账号上的 SSH 公钥，天然只授予一个仓库的
# 权限（默认只读）。配合本地 Host 别名，即可做到「一把钥匙只开一扇门」。
# 官方约束：同一把 deploy key 不能复用到多个仓库，必须一仓一键。
#
# 用法：
#   bash scripts/setup-repo-deploy-key.sh OWNER/REPO [OWNER/REPO ...]
#
# 例：bash scripts/setup-repo-deploy-key.sh myorg/backend myorg/frontend

set -euo pipefail

SSH_DIR="$HOME/.ssh"
BASE_CONF="$SSH_DIR/github.config"
REPO_CONF="$SSH_DIR/github-repos.config"

[ $# -ge 1 ] || { echo "用法: bash $0 OWNER/REPO [OWNER/REPO ...]" >&2; exit 2; }

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# 1) 基础配置：若不存在则创建，并确保 include 了按仓库生成的片段文件
if [ ! -f "$BASE_CONF" ]; then
  cat > "$BASE_CONF" <<'EOF'
# 基础 SSH 配置。
# 必须用 `ssh -F ~/.ssh/github.config` 调用：传 -F 后 OpenSSH 会跳过系统级
# /etc/ssh/ssh_config，从而绕开其中 20-systemd-ssh-proxy.conf 的权限 bug。
EOF
  chmod 600 "$BASE_CONF"
fi

INCLUDE_LINE="Include $REPO_CONF"
if ! grep -qF "$INCLUDE_LINE" "$BASE_CONF"; then
  # 必须插到文件**开头**、任何 Host 块之前。实测：Include 若出现在 Host 块之后，
  # 被包含文件里的 Host 别名完全不生效（ssh -G 会退化成把别名当真实主机名解析）。
  tmp="$BASE_CONF.tmp.$$"
  {
    printf '# 按仓库隔离的 Host 别名（由 scripts/setup-repo-deploy-key.sh 生成）\n'
    printf '# 注意：本行必须位于任何 Host 块之前，否则别名不生效。\n'
    printf '%s\n\n' "$INCLUDE_LINE"
    cat "$BASE_CONF"
  } > "$tmp"
  mv "$tmp" "$BASE_CONF"
  chmod 600 "$BASE_CONF"
  echo "已向 $BASE_CONF 顶部插入 include"
fi

touch "$REPO_CONF"; chmod 600 "$REPO_CONF"

for repo in "$@"; do
  case "$repo" in
    */*) ;;
    *) echo "✗ 参数格式错误：'$repo'，应为 OWNER/REPO" >&2; exit 2 ;;
  esac

  # 别名必须全小写：OpenSSH 在匹配 Host 模式前会先把主机名小写化，而模式匹配
  # 区分大小写。含大写的 Host 模式（如 github-MarsGuBJ-videoai）永远无法命中，
  # 会退化成"把别名当真实主机名去解析"→ Could not resolve hostname。
  slug=$(printf '%s' "$repo" | tr 'A-Z/.' 'a-z--')
  alias="github-$slug"
  key="$SSH_DIR/id_ed25519_$slug"

  # 兼容早期版本生成的含大写文件名（slug 未小写化），避免重复生成新密钥
  if [ ! -f "$key" ]; then
    existing=$(find "$SSH_DIR" -maxdepth 1 -iname "id_ed25519_$slug" -print -quit 2>/dev/null || true)
    if [ -n "$existing" ]; then
      key="$existing"
      echo "· 复用已存在密钥（大小写变体）$key"
    fi
  fi

  # 2) 一仓一键
  if [ -f "$key" ]; then
    echo "· 复用已存在密钥 $key"
  else
    ssh-keygen -t ed25519 -C "deploy:$repo" -f "$key" -N "" -q
    echo "· 已生成新密钥 $key"
  fi
  chmod 600 "$key"; chmod 644 "$key.pub"

  # 3) 写入 Host 别名（幂等）
  if grep -qE "^Host[[:space:]]+$alias\$" "$REPO_CONF"; then
    echo "· 别名 $alias 已存在，跳过"
  else
    cat >> "$REPO_CONF" <<EOF

# $repo
Host $alias
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile $key
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF
    echo "· 已写入别名 $alias"
  fi

  # 4) 只把该仓库的 URL 映射到该别名 —— 白名单式，其他仓库不受影响
  git config --global "url.git@$alias:$repo.insteadOf" "https://github.com/$repo"

  echo
  echo "── $repo ──────────────────────────────────"
  echo "  公钥指纹: $(ssh-keygen -lf "$key.pub" | awk '{print $2}')"
  echo "  需要添加公钥到: https://github.com/$repo/settings/keys"
  echo "    （勾选 'Allow write access' 才能 push；不勾 = 只读）"
  echo "  添加后克隆: git clone git@$alias:$repo.git"
  echo "  或直接用原始 URL（已被 insteadOf 映射）: git clone https://github.com/$repo.git"
  echo "  待添加的公钥内容↓"
  sed 's/^/    /' "$key.pub"
  echo
done

echo "════ 完成。验证方式（把 OWNER/REPO 换成实际仓库）════"
echo "  ssh -F $BASE_CONF -T git@github-<slug>"
echo "  成功时 GitHub 会回显 'Hi OWNER/REPO! You've successfully authenticated'"
