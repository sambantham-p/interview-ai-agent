import type { InterviewDetail, InterviewTurn } from '../../types/api'

export function appendTurn(
  session: InterviewDetail,
  answer: string,
  turn: InterviewTurn,
): InterviewDetail {
  const lastIndex = session.transcript.at(-1)?.index ?? 0
  const phase = session.current_phase

  return {
    ...session,
    ...turn,
    transcript: [
      ...session.transcript,
      {
        index: lastIndex + 1,
        role: 'user',
        text: answer,
        phase,
        hint_level: null,
        red_flag: false,
        anxiety_detected: false,
      },
      {
        index: lastIndex + 2,
        role: 'model',
        text: turn.reply,
        phase,
        hint_level: turn.hint_level,
        red_flag: turn.red_flag,
        anxiety_detected: turn.anxiety_detected,
      },
    ],
  }
}
