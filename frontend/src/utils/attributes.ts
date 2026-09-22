// 搜索结果属性值清洗（文搜图 / 图搜图结果卡片下方的年龄、配饰、衣服颜色、行为）。
// 后端部分属性会返回数组（如 ["青年"]）或带方括号/引号的字符串（如 '["黑色"]'），
// Vue 插值数组时会按 JSON 输出，页面上就会出现 ["青年"] 这类方括号与引号。
// 这里统一去掉方括号与引号，只保留文字，多个值用「、」连接；
// 清洗后没有文字的返回空串，由调用方连同字段名一起隐藏。
export function attributeText(value: unknown): string {
  const parts: string[] = [];
  // 仅由短横线、下划线、点、斜杠组成的占位值（如 "-" "—" "/"）不算文字
  const placeholderOnly = /^[-—–_./\\]+$/;
  const collect = (input: unknown) => {
    if (input === null || input === undefined) return;
    if (Array.isArray(input)) {
      input.forEach(collect);
      return;
    }
    if (typeof input === "object") {
      // 兼容 { value: "青年" } / { label: "青年" } 这类结构化属性
      const record = input as Record<string, unknown>;
      const nested = record.value ?? record.label ?? record.name ?? record.text;
      if (nested !== undefined) collect(nested);
      return;
    }
    const text = String(input)
      // 去掉方括号与中英文引号
      .replace(/[\[\]"'“”‘’]/g, "")
      .replace(/\s+/g, " ")
      .trim();
    if (!text) return;
    text
      .split(/[,，、;；]/)
      .map((part) => part.trim())
      .filter((part) => part && !placeholderOnly.test(part))
      .forEach((part) => parts.push(part));
  };
  collect(value);
  return parts.join("、");
}
