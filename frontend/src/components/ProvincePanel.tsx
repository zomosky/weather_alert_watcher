import { ProvinceItem } from "../types";

type Props = {
  provinces: ProvinceItem[];
};

export function ProvincePanel({ provinces }: Props) {
  return (
    <section className="card">
      <h3>省份排序与高亮</h3>
      <div className="province-grid">
        {provinces.map((item) => (
          <div key={item.name} className={item.highlighted ? "province highlighted" : "province"}>
            <span>{item.name}</span>
            <small>{item.pinyin_initial}</small>
          </div>
        ))}
      </div>
    </section>
  );
}
