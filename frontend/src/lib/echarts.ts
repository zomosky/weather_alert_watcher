import * as echarts from "echarts/core";
import { LineChart, MapChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent, VisualMapPiecewiseComponent, MarkPointComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, MapChart, GridComponent, LegendComponent, TooltipComponent, VisualMapPiecewiseComponent, MarkPointComponent, CanvasRenderer]);
export { echarts };
