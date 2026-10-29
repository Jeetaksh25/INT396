import { TreeStructure } from "@phosphor-icons/react/dist/ssr";
import { getModelCard } from "@/lib/api";
import { ModelCard } from "@/lib/types";
import { PageHead, Section, KvList, MetricCard } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { ClassBars, ImportanceBars } from "@/components/charts";
import { BlurFade } from "@/components/ui/blur-fade";

const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;

const groupNames: Record<string, string> = {
  normal: "Normal",
  fault: "Fault",
  extreme: "Extreme",
};

const stationNames: Record<string, string> = {
  DEL: "Delhi",
  BOM: "Mumbai",
  MAA: "Chennai",
  HYD: "Hyderabad",
  JAI: "Jaipur",
  CCU: "Kolkata",
  BLR: "Bengaluru",
  SLM: "Shimla",
};

export default async function ModelPage() {
  let card: ModelCard;
  try {
    card = await getModelCard();
  } catch (caught) {
    const message = caught instanceof Error ? caught.message : "unknown error";
    return (
      <>
        <TopBar />
        <PageHead title="Model card" description="Model metadata could not be loaded." />
        <div className="error-panel">
          <h2 className="error-title">Model card unavailable</h2>
          <p className="code-line">{message}</p>
          <p className="code-line">cd backend &amp;&amp; python generate_data.py &amp;&amp; python model.py</p>
        </div>
      </>
    );
  }

  const confusion = card.group_confusion;
  const rowTotals = confusion.matrix.map((row) => row.reduce((sum, value) => sum + value, 0));

  return (
    <>
      <TopBar />
      <PageHead
        size="large"
        title="The model, in full"
        description={card.task + "."}
        aside={
          <>
            <span className="chip" data-tone="accent">
              <TreeStructure size={12} weight="bold" />
              supervised
            </span>
            <span>
              {card.model.name} · {card.model.trees} trees · {card.features.length} features
            </span>
            <span className="mono-label" style={{ letterSpacing: 0 }}>
              seed {card.random_seed} · {card.timing.total_seconds}s to train and evaluate
            </span>
          </>
        }
      />

      <div className="metric-grid">
        <MetricCard
          label="Accuracy"
          value={card.grouped.accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption="normal, fault or extreme"
          delay={0.02}
        />
        <MetricCard
          label="Balanced accuracy"
          value={card.grouped.balanced_accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption="mean recall of the three groups"
          delay={0.06}
        />
        <MetricCard
          label="Macro F1"
          value={card.grouped.macro_f1}
          decimals={3}
          caption={`range check ${card.range_check.macro_f1.toFixed(3)}`}
          delay={0.1}
        />
        <MetricCard
          label="Eleven-class accuracy"
          value={card.detailed.accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption={`macro F1 ${card.detailed.macro_f1.toFixed(3)}`}
          delay={0.14}
        />
      </div>

      <div className="cols-2">
        <Section title="Model" note="One estimator, kept simple on purpose.">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card card-pad">
              <KvList
                rows={[
                  { key: "Algorithm", value: card.model.name },
                  { key: "Trees", value: card.model.trees },
                  { key: "Max depth", value: card.model.max_depth },
                  { key: "Min samples per leaf", value: card.model.min_samples_leaf },
                  { key: "Library", value: "scikit-learn" },
                  { key: "Why", value: card.model.why },
                ]}
              />
            </div>
          </BlurFade>
        </Section>

        <Section title="Data and evaluation" note="Nothing is scored on a station it trained on.">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card card-pad">
              <KvList
                rows={[
                  { key: "Source", value: card.dataset.source },
                  { key: "Period", value: `${card.dataset.start.slice(0, 10)} to ${card.dataset.end.slice(0, 10)}` },
                  { key: "Readings", value: card.dataset.rows.toLocaleString() },
                  {
                    key: "Train / test per fold",
                    value: `${card.dataset.train_rows_per_fold.toLocaleString()} / ${card.dataset.test_rows_per_fold.toLocaleString()}`,
                  },
                  { key: "Split", value: card.evaluation },
                  { key: "Always predict normal", value: percent(card.majority_baseline) },
                ]}
              />
            </div>
          </BlurFade>
        </Section>
      </div>

      <Section title="Confusion matrix" note="Rows are the truth, columns the prediction, with the share of each true group.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="card-flat">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Truth</th>
                    {confusion.labels.map((label) => (
                      <th key={label} style={{ textAlign: "right" }}>
                        predicted {groupNames[label].toLowerCase()}
                      </th>
                    ))}
                    <th style={{ textAlign: "right" }}>readings</th>
                  </tr>
                </thead>
                <tbody>
                  {confusion.matrix.map((row, i) => (
                    <tr key={confusion.labels[i]}>
                      <td className="cell-strong">{groupNames[confusion.labels[i]]}</td>
                      {row.map((value, j) => (
                        <td
                          key={j}
                          style={{
                            textAlign: "right",
                            fontVariantNumeric: "tabular-nums",
                            fontWeight: i === j ? 600 : 400,
                            color: i === j ? "var(--ink)" : "var(--ink-3)",
                          }}
                        >
                          {value.toLocaleString()}
                          <small style={{ marginLeft: "0.4rem" }}>{percent(value / rowTotals[i])}</small>
                        </td>
                      ))}
                      <td style={{ textAlign: "right" }} className="cell-muted">
                        {rowTotals[i].toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </BlurFade>
      </Section>

      <div className="cols-2">
        <Section title="Per-class scores" note="Recall is the share of a class found; precision is the share of predictions that were right.">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card card-pad">
              <ClassBars perClass={card.per_class} />
            </div>
          </BlurFade>
        </Section>

        <Section title="Feature importance" note="Mean decrease in impurity across the forest.">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card card-pad">
              <ImportanceBars importance={card.feature_importance} />
            </div>
          </BlurFade>
        </Section>
      </div>

      <Section title="Per station" note="Each station scored by the fold that held it out.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="card-flat">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Station</th>
                    <th style={{ textAlign: "right" }}>Accuracy</th>
                    <th style={{ textAlign: "right" }}>Balanced accuracy</th>
                    <th style={{ textAlign: "right" }}>Macro F1</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(card.per_station).map(([code, row]) => (
                    <tr key={code}>
                      <td>
                        <span className="station-cell">
                          <span className="station-id">{code}</span>
                          <span className="cell-strong">{stationNames[code] ?? code}</span>
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }}>{percent(row.accuracy)}</td>
                      <td style={{ textAlign: "right" }}>{percent(row.balanced_accuracy)}</td>
                      <td style={{ textAlign: "right" }}>{row.macro_f1.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </BlurFade>
      </Section>

      <Section title="Events" note="Consecutive flagged hours on one sensor, merged into one episode.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="card card-pad">
            <KvList
              rows={[
                { key: "Episodes found", value: card.events.count.toLocaleString() },
                { key: "Fault episodes", value: card.events.fault_events.toLocaleString() },
                { key: "Extreme episodes", value: card.events.extreme_events.toLocaleString() },
                { key: "Episodes with the right group", value: percent(card.events.correct_events) },
              ]}
            />
          </div>
        </BlurFade>
      </Section>
    </>
  );
}
