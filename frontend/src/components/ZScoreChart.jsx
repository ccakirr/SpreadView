import { useEffect, useRef } from "react";
import {
  createChart,
  LineSeries,
  LineStyle,
} from "lightweight-charts";

function ZScoreChart({ data }) {
  const chartContainerRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data?.length) {
      return;
    }

    const chart = createChart(chartContainerRef.current, {
      autoSize: true,

      layout: {
        background: {
          color: "#0d1117",
        },
        textColor: "#8b949e",
      },

      grid: {
        vertLines: {
          color: "#21262d",
        },
        horzLines: {
          color: "#21262d",
        },
      },

      rightPriceScale: {
        borderColor: "#30363d",
      },

      timeScale: {
        borderColor: "#30363d",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const zscoreSeries = chart.addSeries(LineSeries, {
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });

    const chartData = data.map((item) => ({
      time: item.time,
      value: item.zscore,
    }));

    zscoreSeries.setData(chartData);

    zscoreSeries.createPriceLine({
      price: 2,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: "+2",
    });

    zscoreSeries.createPriceLine({
      price: 0,
      lineWidth: 1,
      lineStyle: LineStyle.Solid,
      axisLabelVisible: true,
      title: "Mean",
    });

    zscoreSeries.createPriceLine({
      price: -2,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: "-2",
    });

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [data]);

  return (
    <div className="zscore-chart">
      <div ref={chartContainerRef} className="chart-container" />
    </div>
  );
}

export default ZScoreChart;