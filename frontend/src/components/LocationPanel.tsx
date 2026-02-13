import { FormEvent, useState } from "react";
import { SelectedLocation } from "../types";

type Props = {
  value: SelectedLocation;
  onChange: (next: SelectedLocation) => void;
  onSubmit: () => void;
};

const PROVINCES = [
  "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建",
  "江西", "山东", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海",
  "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门", "台湾",
];

export function LocationPanel({ value, onChange, onSubmit }: Props) {
  const [geoMessage, setGeoMessage] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  const locate = () => {
    if (!navigator.geolocation) {
      setGeoMessage("当前浏览器不支持定位，请手动输入经纬度或省份。");
      return;
    }
    setGeoMessage("正在请求定位权限...");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        onChange({
          ...value,
          lat: Number(pos.coords.latitude.toFixed(4)),
          lon: Number(pos.coords.longitude.toFixed(4)),
        });
        setGeoMessage("定位成功，已更新经纬度。");
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setGeoMessage("定位被拒绝，请在浏览器中允许定位权限后重试。");
          return;
        }
        if (err.code === err.TIMEOUT) {
          setGeoMessage("定位超时，请重试或手动输入经纬度。");
          return;
        }
        setGeoMessage("定位失败，请重试或手动输入经纬度。");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  return (
    <form className="card location" onSubmit={handleSubmit}>
      <h3>位置输入</h3>
      <div className="grid-2">
        <label>
          纬度
          <input
            type="number"
            step="0.0001"
            value={value.lat}
            onChange={(e) => onChange({ ...value, lat: Number(e.target.value) })}
          />
        </label>
        <label>
          经度
          <input
            type="number"
            step="0.0001"
            value={value.lon}
            onChange={(e) => onChange({ ...value, lon: Number(e.target.value) })}
          />
        </label>
      </div>
      <label>
        省份
        <select value={value.province ?? ""} onChange={(e) => onChange({ ...value, province: e.target.value })}>
          {PROVINCES.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <label>
        地址（可选）
        <input
          value={value.address ?? ""}
          onChange={(e) => onChange({ ...value, address: e.target.value || undefined })}
          placeholder="当前版本仅展示经纬度，可手动备注"
        />
      </label>
      <p className="meta coord-display">
        当前经纬度：{value.lat.toFixed(4)}, {value.lon.toFixed(4)}
      </p>
      <div className="row">
        <button type="button" onClick={locate}>定位</button>
        <button type="submit">更新看板</button>
      </div>
      {geoMessage && <p className="meta geo-msg">{geoMessage}</p>}
    </form>
  );
}
