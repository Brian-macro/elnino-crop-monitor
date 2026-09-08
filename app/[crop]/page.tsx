import { notFound } from "next/navigation";
import Dashboard from "@/components/Dashboard";
const crops = ["wheat", "corn", "soybean", "rice", "sugar"];
export function generateStaticParams() {
  return crops.map((crop) => ({ crop }));
}
export default function Page({ params }: { params: { crop: string } }) {
  if (!crops.includes(params.crop)) notFound();
  return <Dashboard initialCrop={params.crop} />;
}
