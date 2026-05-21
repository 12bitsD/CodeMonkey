export const MASTERY_PASS_THRESHOLD = 2;

export function hashText(value) {
  const text = String(value || "");
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return hash.toString(16);
}

export function buildMasteryCheckKey(nodeId, index, standard) {
  return `${nodeId}:${index}:${hashText(standard)}`;
}

function rotateOptions(options, seed) {
  const offset = seed % options.length;
  return options.slice(offset).concat(options.slice(0, offset));
}

function withAnswer(options, correctText, seed) {
  const rotated = rotateOptions(options, seed);
  return {
    options: rotated,
    answerIndex: rotated.indexOf(correctText),
  };
}

export function generateMasteryQuiz({ nodeName, standard }) {
  const topic = nodeName || "当前知识点";
  const check = standard || "这条掌握标准";
  const seed = hashText(`${topic}:${check}`).length;

  const q1Correct = `能独立完成并解释：${check}`;
  const q1 = withAnswer(
    [
      q1Correct,
      `只看过一次「${topic}」相关材料`,
      "能说出几个关键词，但无法完成实际任务",
      "复制现成答案后得到相同结果",
    ],
    q1Correct,
    seed,
  );

  const q2Correct = "先判断任务要求，再独立完成关键步骤，并能说明为什么这样做";
  const q2 = withAnswer(
    [
      "遇到不会的地方立刻跳过，不验证结果",
      q2Correct,
      "只背诵定义，不做任何例子或应用",
      "只要结果看起来正确，就不需要解释过程",
    ],
    q2Correct,
    seed + 1,
  );

  const q3Correct = "只能跟着示例照抄，换一个条件就不知道怎么做";
  const q3 = withAnswer(
    [
      "能指出关键前提、常见错误和验证方式",
      "能把同一方法迁移到相近场景",
      q3Correct,
      "能用自己的话解释标准背后的原因",
    ],
    q3Correct,
    seed + 2,
  );

  return [
    {
      question: `哪种表现最能说明你已经掌握「${topic}」中的这条标准？`,
      explanation: "掌握标准强调可验证的输出，不只是看过或记住。",
      ...q1,
    },
    {
      question: `围绕「${check}」，遇到实际题目时最合理的做法是？`,
      explanation: "真正掌握需要能独立完成关键步骤，并说明判断依据。",
      ...q2,
    },
    {
      question: "以下哪种情况说明还没有真正通过这条掌握标准？",
      explanation: "只能照抄示例通常说明还没有形成可迁移的理解。",
      ...q3,
    },
  ];
}
