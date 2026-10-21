import { PageHead } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { SimulationStudio } from "@/components/simulation-studio";

export const metadata = {
  title: "Simulation",
  description:
    "Generate a random weather window, inject sensor faults, and watch the detector classify every reading in real time.",
};

export default function SimulationPage() {
  return (
    <>
      <TopBar />
      <PageHead
        size="large"
        title="Watch it decide."
        description="A fresh 21-day window, fresh faults, and the real model scoring every reading. Press generate and the pipeline runs end to end — then each reading is replayed into the lane the model chose, scored against ground truth."
        aside={
          <>
            <span>21-day window</span>
            <span>5 detectors · 3-of-5 vote</span>
          </>
        }
      />
      <SimulationStudio />
    </>
  );
}
