import { getDecisionBrief, type DecisionBriefData } from "../../lib/api";
import { ApiErrorAlert } from "../../../components/states/api-error";
import { BriefForm } from "./BriefForm";

export const dynamic = "force-dynamic";

const PEER_QUESTIONS = [
  "Hvilket problem startede I med — og hvorfor netop det?",
  "Hvad målte I før og efter (volumen, AHT, løsningsgrad, CSAT)?",
  "Hvor lang tid fra beslutning til første effekt i drift?",
  "Hvad gik galt eller tog længere tid end forventet?",
  "Hvordan tog medarbejderne og kunderne imod det?",
  "Hvad koster det årligt, og hvad ville I gøre anderledes i dag?",
];

export default async function AdminDecisionBriefPage() {
  let data: DecisionBriefData | null = null;
  let loadError: unknown = null;
  try {
    data = await getDecisionBrief();
  } catch (error) {
    loadError = error;
  }

  return (
    <>
      <h1>OK-tal og beslutningsoplæg</h1>
      <p className="page-lead">
        Tallene her er OK&#8217;s egne og indtastes manuelt; de bruges kun i
        beslutningsoplæggets regneeksempel. Intet her deles med AI eller kilder
        uden for radaren. Kræver Admin for at gemme.
      </p>
      {data === null ? (
        <ApiErrorAlert error={loadError} />
      ) : (
        <BriefForm initial={data.brief} />
      )}

      <section
        className="signal-section"
        aria-label="Spørgsmål til branchekolleger"
      >
        <h2 className="section-title">
          Spørgsmål til branchekolleger (fx Andel Energi, Norlys)
        </h2>
        <ol>
          {PEER_QUESTIONS.map((question) => (
            <li key={question}>{question}</li>
          ))}
        </ol>
      </section>
    </>
  );
}
