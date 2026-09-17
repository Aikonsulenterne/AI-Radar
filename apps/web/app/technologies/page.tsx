import { EmptyState } from "../components/EmptyState";

export default function TechnologiesPage() {
  return (
    <>
      <h1>Teknologiradar</h1>
      <p className="page-lead">
        Kuraterede AI-capabilities i tre horisonter: NU (modent og anvendeligt),
        NÆSTE (bør undersøges) og HORIZON (1&#8211;3 år, højere usikkerhed).
        Modenhed, adoption, dokumenteret værdi, momentum og overførbarhed holdes
        adskilt — ingen samlet score.
      </p>
      <EmptyState slice="Slice 4">
        Teknologiprofilerne oprettes sammen med adoption-visningen.
      </EmptyState>
    </>
  );
}
