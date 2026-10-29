import Link from "next/link";
import { ArrowUpRight, WarningCircle } from "@phosphor-icons/react/dist/ssr";
import { getMetrics } from "@/lib/api";
import { MetricsSummary } from "@/lib/types";
import { PageHead, Section, StepList, Callout, KvList } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { BlurFade } from "@/components/ui/blur-fade";

const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;

const featureNotes: Record<string, string> = {
  value_z: "reading standardised by its own station and sensor",
  dev_day: "distance from the centred 24 hour median",
  dev_week: "24 hour median minus the two week median, catches bias and drift",
  jump: "change from the previous hour",
  noise_6h: "spread of hourly changes over 6 hours",
  noise_day: "spread of hourly changes over 24 hours, catches lost precision",
  flat_6h: "identical consecutive readings in 6 hours, catches a stuck sensor",
  missing_6h: "missing readings in 6 hours, catches dropout",
  others_dev: "how far the other three sensors at the station moved",
  others_week: "slow movement of the other three sensors",
  temp_week: "slow movement of the station's temperature",
  humid_week: "slow movement of the station's humidity",
  wind_week: "slow movement of the station's wind speed",
  press_week: "slow movement of the station's pressure",
  sensor_code: "which of the four sensors the reading is from",
  hour: "hour of the day",
};

export default async function MethodPage() {
  let metrics: MetricsSummary | null = null;
  let error: string | null = null;

  try {
    metrics = await getMetrics();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "unknown error";
  }

  if (error || !metrics) {
    return (
      <>
        <TopBar />
        <PageHead title="Method" description="Metrics could not be loaded." />
        <div className="error-panel">
          <h2 className="error-title">Metrics unavailable</h2>
          <p className="code-line">{error}</p>
        </div>
      </>
    );
  }

  const counts = metrics.label_counts;

  return (
    <>
      <TopBar />
      <PageHead
        size="large"
        title="How a reading is judged"
        description="Labelled faults and extremes are injected into real weather data, sixteen features describe every reading, and a Random Forest learns which pattern is which. A fixed range check runs beside it as the baseline."
        aside={
          <>
            <span>{counts.total_readings.toLocaleString()} readings</span>
            <span>seed {metrics.random_seed} · {metrics.features.length} features</span>
          </>
        }
      />

      <Section title="The pipeline, in order" note="Two Python files, four stages.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="card card-pad">
            <StepList
              steps={[
                {
                  title: "Load real readings",
                  body: (
                    <>
                      One year of hourly temperature, humidity, wind speed and pressure for eight
                      Indian stations from the Open-Meteo ERA5 archive (<code>generate_data.py</code>).
                    </>
                  ),
                },
                {
                  title: "Inject labelled events",
                  body: (
                    <>
                      Six sensor faults on a single sensor at a time, and four weather extremes that
                      move several sensors of a station together in their usual season. Each changed
                      reading gets its label, giving {percent(counts.fault / counts.total_readings, 2)}{" "}
                      fault and {percent(counts.extreme / counts.total_readings, 2)} extreme readings.
                    </>
                  ),
                },
                {
                  title: "Build features",
                  body: (
                    <>
                      Rolling medians, noise, flat-line and missing counts for each sensor, plus how the
                      other sensors of the same station are moving (<code>model.py</code>).
                    </>
                  ),
                },
                {
                  title: "Train and evaluate",
                  body: (
                    <>
                      A Random Forest of {metrics.model.trees} trees is scored with 4-fold cross
                      validation grouped by station, so every prediction comes from a model that never
                      saw that station.
                    </>
                  ),
                },
              ]}
            />
          </div>
        </BlurFade>
      </Section>

      <div className="cols-2">
        <Section title="What gets injected" note="Eleven classes in total.">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card card-pad">
              <KvList
                rows={[
                  { key: "Bias", value: "constant offset of 4 to 7 standard deviations" },
                  { key: "Drift", value: "offset that grows slowly over 3 to 7 days" },
                  { key: "Stuck", value: "the sensor repeats one value for 12 to 48 hours" },
                  { key: "Spike", value: "isolated readings 6 to 10 deviations off" },
                  { key: "Precision", value: "coarse rounding plus noise" },
                  { key: "Dropout", value: "readings go missing for 6 to 24 hours" },
                  { key: "Heat wave", value: "temperature up, humidity and pressure down, Apr to Jun" },
                  { key: "Cold snap", value: "temperature down, wind and humidity up, Dec to Feb" },
                  { key: "Storm", value: "wind up, pressure down, humidity up, Jun to Oct" },
                  { key: "Heavy rain", value: "humidity up, temperature down, Jun to Sep" },
                ]}
              />
            </div>
          </BlurFade>
        </Section>

        <Section title="The features" note="Everything the forest sees.">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card card-pad">
              <KvList
                rows={metrics.features.map((name) => ({
                  key: name,
                  value: featureNotes[name] ?? "",
                }))}
              />
            </div>
          </BlurFade>
        </Section>
      </div>

      <Section title="Against the baseline" note="Same readings, same labels.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="card card-pad">
            <KvList
              rows={[
                {
                  key: "Accuracy",
                  value: `${percent(metrics.range_check.accuracy)} → ${percent(metrics.grouped.accuracy)}`,
                },
                {
                  key: "Balanced accuracy",
                  value: `${percent(metrics.range_check.balanced_accuracy)} → ${percent(metrics.grouped.balanced_accuracy)}`,
                },
                {
                  key: "Macro F1",
                  value: `${metrics.range_check.macro_f1.toFixed(3)} → ${metrics.grouped.macro_f1.toFixed(3)}`,
                },
                {
                  key: "Always predict normal",
                  value: percent(metrics.majority_baseline),
                },
              ]}
            />
          </div>
        </BlurFade>
      </Section>

      <Section title="Limits" note="Said plainly.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <Callout icon={<WarningCircle size={18} weight="regular" aria-hidden="true" />}>
            <p>
              The labels come from injection, so the model learns the injected patterns. Short
              heavy-rain events and the first hours of a slow drift are the hardest cases. On a real
              network the numbers would be lower until it is retrained on logged failures.{" "}
              <Link href="/model" className="row-link">
                Full scores
                <ArrowUpRight size={12} weight="bold" style={{ display: "inline" }} />
              </Link>
            </p>
          </Callout>
        </BlurFade>
      </Section>
    </>
  );
}
