import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import { Button, Modal } from "../ui";
import { MASTERY_PASS_THRESHOLD } from "../../utils/masteryQuiz";
import { useLanguage } from "../../contexts/LanguageContext";

export default function MasteryQuizModal({ quiz, onClose, onPassed }) {
  const { t } = useLanguage();
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    setAnswers({});
    setSubmitted(false);
  }, [quiz?.key]);

  const score = useMemo(() => {
    if (!quiz?.questions) return 0;
    return quiz.questions.reduce(
      (total, question, index) =>
        total + (answers[index] === question.answerIndex ? 1 : 0),
      0,
    );
  }, [answers, quiz]);

  if (!quiz) return null;

  const complete = Object.keys(answers).length === quiz.questions.length;
  const passed = submitted && score >= MASTERY_PASS_THRESHOLD;

  const handleSubmit = () => {
    if (!complete) return;
    setSubmitted(true);
    if (score >= MASTERY_PASS_THRESHOLD) {
      onPassed?.({
        key: quiz.key,
        nodeId: quiz.nodeId,
        index: quiz.index,
        score,
        total: quiz.questions.length,
      });
    }
  };

  const handleRetry = () => {
    setAnswers({});
    setSubmitted(false);
  };

  return (
    <Modal
      isOpen={Boolean(quiz)}
      onClose={onClose}
      title={t("quiz.title")}
      footer={
        submitted ? (
          <>
            <Button variant="ghost" onClick={onClose}>
              {t("common.close")}
            </Button>
            {!passed && (
              <Button icon={RotateCcw} onClick={handleRetry}>
                {t("quiz.retry")}
              </Button>
            )}
          </>
        ) : (
          <>
            <Button variant="ghost" onClick={onClose}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleSubmit} disabled={!complete}>
              {t("quiz.submit")}
            </Button>
          </>
        )
      }
    >
      <div className="space-y-5">
        <div className="rounded-2xl border border-zinc-100 bg-zinc-50/80 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
            {t("quiz.standard")}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-zinc-800">
            {quiz.standard}
          </p>
          <p className="mt-3 text-xs text-zinc-400">
            {t("quiz.help")}
          </p>
        </div>

        {submitted && (
          <div
            className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${
              passed
                ? "border-teal-200 bg-teal-50 text-teal-800"
                : "border-amber-200 bg-amber-50 text-amber-800"
            }`}
          >
            {passed ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
            <div>
              <p className="text-sm font-semibold">
                {passed ? t("quiz.passed") : t("quiz.notYet")}
              </p>
              <p className="text-xs opacity-80">
                {t("quiz.score", { score, total: quiz.questions.length })}
              </p>
            </div>
          </div>
        )}

        <div className="space-y-5">
          {quiz.questions.map((question, questionIndex) => {
            const selected = answers[questionIndex];
            return (
              <section key={questionIndex} className="space-y-3">
                <h4 className="text-sm font-semibold leading-relaxed text-zinc-900">
                  {questionIndex + 1}. {question.question}
                </h4>
                <div className="space-y-2">
                  {question.options.map((option, optionIndex) => {
                    const chosen = selected === optionIndex;
                    const correct = question.answerIndex === optionIndex;
                    const showResult = submitted && (chosen || correct);
                    return (
                      <button
                        key={option}
                        type="button"
                        disabled={submitted}
                        onClick={() =>
                          setAnswers((prev) => ({
                            ...prev,
                            [questionIndex]: optionIndex,
                          }))
                        }
                        className={`flex w-full items-start gap-3 rounded-2xl border px-3 py-2.5 text-left text-sm leading-relaxed transition-colors ${
                          showResult && correct
                            ? "border-teal-300 bg-teal-50 text-teal-800"
                            : showResult && chosen
                              ? "border-red-200 bg-red-50 text-red-700"
                              : chosen
                                ? "border-zinc-900 bg-zinc-900 text-white"
                                : "border-zinc-100 bg-white text-zinc-700 hover:border-zinc-200 hover:bg-zinc-50"
                        }`}
                      >
                        <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border border-current text-[11px] font-semibold">
                          {String.fromCharCode(65 + optionIndex)}
                        </span>
                        <span>{option}</span>
                      </button>
                    );
                  })}
                </div>
                {submitted && (
                  <p className="rounded-xl bg-zinc-50 px-3 py-2 text-xs leading-relaxed text-zinc-500">
                    {question.explanation}
                  </p>
                )}
              </section>
            );
          })}
        </div>
      </div>
    </Modal>
  );
}
