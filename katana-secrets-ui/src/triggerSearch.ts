// src/triggerSearch.ts

interface Trigger {
  keywords: string[];
  response: string | (() => string);
  matchType?: 'exact' | 'contains';
}

const triggers: Trigger[] = [
  { keywords: ["привет", "hello", "hi", "здравствуй", "start"], response: "Приветствую, капитан! Катана на связи. Чем могу помочь?" },
  { keywords: ["катана", "katana"], response: "Я — твой клинок и твоя память. Командуй!" },
  { keywords: ["помощь", "help", "что ты умеешь", "info"], response: "Отправь команду или спроси что-нибудь. Я могу искать информацию в памяти или выполнять действия. Доступные триггеры: привет, катана, память, статус, секреты, время, помощь." },
  { keywords: ["время", "time", "сколько времени"], response: () => \`Текущее время: \${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}\` },
  { keywords: ["память", "memory", "помнишь"], response: "Память Катаны активна и хранит все наши диалоги." },
  { keywords: ["статус", "status"], response: "Все системы Катаны функционируют в штатном режиме. Готова к выполнению команд." },
  { keywords: ["секреты", "secrets", "ключи"], response: "Управление секретами - моя основная задача. Для просмотра используйте соответствующий раздел UI (пока не реализован в этом MVP чате)." },
  { keywords: ["пока", "bye", "exit", "quit"], response: "До связи, капитан. Катана всегда на страже."}
];

export function triggerSearch(input: string): string | null {
  const lowerInput = input.toLowerCase().trim();
  if (!lowerInput) return null;

  for (const trig of triggers) {
    const matchType = trig.matchType || 'contains';
    let found = false;
    for (const keyword of trig.keywords) {
      if (matchType === 'contains' && lowerInput.includes(keyword.toLowerCase())) {
        found = true;
        break;
      } else if (matchType === 'exact' && lowerInput === keyword.toLowerCase()) {
        found = true;
        break;
      }
    }
    if (found) {
      return typeof trig.response === 'function' ? trig.response() : trig.response;
    }
  }
  return null;
}
