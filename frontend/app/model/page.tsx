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
              unsupervised + booster
            </span>
            <span>
              {card.unsupervised.detectors.length} detectors · {card.model.trees}-tree booster ·{" "}
              {card.features.length} features
            </span>
            <span className="mono-label" style={{ letterSpacing: 0 }}>
              seed {card.random_seed} · {card.timing.total_seconds}s to train and evaluate
            </span>
          </>
        }
      />

      <div className="metric-grid">
        <MetricCard
          label="Unsupervised accuracy"
          value={card.unsupervised.grouped.accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption={`balanced ${percent(card.unsupervised.grouped.balanced_accuracy)} · F1 ${card.unsupervised.grouped.macro_f1.toFixed(3)}`}
          delay={0.02}
        />
        <MetricCard
          label="Boosted accuracy"
          value={card.grouped.accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption="normal, fault or extreme"
          delay={0.06}
        />
        <MetricCard
          label="Boosted balanced accuracy"
          value={card.grouped.balanced_accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption={`macro F1 ${card.grouped.macro_f1.toFixed(3)}`}
          delay={0.1}
        />
        <MetricCard
          label="Boosted eleven-class accuracy"
          value={card.detailed.accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption={`macro F1 ${card.detailed.macro_f1.toFixed(3)}`}
          delay={0.14}
        />
      </div>

      <div className="cols-2">
        <Section title="Unsupervised detectors" note="Fitted without labels on a random sample of readings.">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card card-pad">
              <KvList
                rows={[
                  { key: "Isolation Forest", value: `${card.unsupervised.isolation_trees} trees · votes on ${percent(card.unsupervised.vote_rates.isolation)}` },
                  { key: "Local Outlier Factor", value: `${card.unsupervised.lof_neighbours} neighbours · votes on ${percent(card.unsupervised.vote_rates.lof)}` },
                  { key: "k-Means distance", value: `${card.unsupervised.kmeans_clusters} clusters · votes on ${percent(card.unsupervised.vote_rates.kmeans)}` },
                  { key: "PCA reconstruction", value: `${card.unsupervised.pca_components} components · votes on ${percent(card.unsupervised.vote_rates.pca)}` },
                  { key: "Fit sample", value: card.unsupervised.fit_sample.toLocaleString() },
                  { key: "Flag rule", value: `${card.unsupervised.votes_needed} of ${card.unsupervised.detectors.length} votes · ${percent(card.unsupervised.flag_rate)} flagged` },
                  { key: "Fault or extreme", value: `extreme when other sensors move more than ${card.unsupervised.coherence_threshold}σ` },
                ]}
              />
            </div>
          </BlurFade>
        </Section>

        <Section title="Unsupervised confusion" note="Rows are the truth, share of each row.">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card-flat">
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Truth</th>
                      {card.unsupervised.group_confusion.labels.map((label) => (
                        <th key={label} style={{ textAlign: "right" }}>
                          {groupNames[label].toLowerCase()}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {card.unsupervised.group_confusion.matrix.map((row, i) => {
                      const total = row.reduce((sum, value) => sum + value, 0);
                      return (
                        <tr key={i}>
                          <td className="cell-strong">{groupNames[card.unsupervised.group_confusion.labels[i]]}</td>
                          {row.map((value, j) => (
                            <td key={j} style={{ textAlign: "right", fontWeight: i === j ? 600 : 400 }}>
                              {percent(value / total)}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </BlurFade>
        </Section>
      </div>

      <div className="cols-2">
        <Section title="Supervised booster" note="Refines the detector verdicts.">
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

      <Section title="Boosted confusion matrix" note="Rows are the truth, columns the prediction, with the share of each true group.">
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
