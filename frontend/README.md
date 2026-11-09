# Frontend · Station Integrity dashboard

The web dashboard for the sensor-fault project. It reads everything from the FastAPI service in `../backend`, so start the backend first.

## Stack

Next.js 16 (App Router), React 19, Tailwind CSS 4, Recharts for charts and Motion for animation.

## Pages

| Route | What it shows |
|---|---|
| `/` | Overview: headline metrics, 30-day network timeline and a ranked station health table |
| `/stations` | All eight stations with their current status and anomaly rate |
| `/stations/[station_id]` | One station: sensor summaries, time series and recent detections |
| `/events` | Detected fault and extreme events |
| `/simulation` | Live simulation: a fresh 21-day window scored by the detectors and the booster |
| `/method` | How the model works, with the live numbers |
| `/model` | Model card: detectors, booster, confusion matrices and per-class results |

## Running

```bash
npm install
npm run dev
```

Open `http://localhost:3000`. Keep the dashboard on port 3000: the API's CORS allowlist only includes `localhost:3000` and `127.0.0.1:3000`, and the event ticker calls the API from the browser.

`NEXT_PUBLIC_API_URL` sets the API address (default `http://127.0.0.1:8000`).

For a production build run `npm run build` and then `npm start`.

## Layout

| Path | What it is |
|---|---|
| `app/` | Pages, plus the `app/api/` route handlers that proxy the API for client components |
| `components/` | Feature components: simulation studio, charts, event ticker, navigation and top bar |
| `components/ui/` | Reusable primitives |
| `lib/api.ts` | Typed fetch wrappers, one per API endpoint |
| `lib/types.ts`, `lib/simulation-types.ts` | Response types that mirror the backend |
