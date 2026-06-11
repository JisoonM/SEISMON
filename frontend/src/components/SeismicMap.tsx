"use client";

import { Crosshair, Flame, Layers, MapPinned, RotateCcw } from "lucide-react";
import mapboxgl from "mapbox-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import type { MutableRefObject } from "react";

import { formatDepth, formatMagnitude } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboardStore";
import type { Earthquake } from "@/types/earthquake";

interface SeismicMapProps {
  events: Earthquake[];
}

type EarthquakeFeature = GeoJSON.Feature<
  GeoJSON.Point,
  {
    id: string;
    magnitude: number;
    alert_level: Earthquake["alert_level"];
    place: string;
    province: string;
    depth_km: number;
    occurred_at: string;
  }
>;

const PHILIPPINES_CENTER: [number, number] = [122.5, 12.0];
const DEFAULT_ZOOM = 4.7;

function toFeatureCollection(events: Earthquake[]): GeoJSON.FeatureCollection<GeoJSON.Point, EarthquakeFeature["properties"]> {
  return {
    type: "FeatureCollection",
    features: events.map((event) => ({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [event.longitude, event.latitude]
      },
      properties: {
        id: event.id,
        magnitude: event.magnitude,
        alert_level: event.alert_level,
        place: event.place,
        province: event.province ?? "Offshore",
        depth_km: event.depth_km,
        occurred_at: event.occurred_at
      }
    }))
  };
}

function newestEvent(events: Earthquake[]) {
  return [...events].sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())[0] ?? null;
}

function flyToSignificantEvent(map: mapboxgl.Map, event: Earthquake | null, lastFlyToEventRef: MutableRefObject<string | null>) {
  if (!event || event.magnitude < 5 || lastFlyToEventRef.current === event.id) {
    return;
  }

  lastFlyToEventRef.current = event.id;
  map.flyTo({
    center: [event.longitude, event.latitude],
    zoom: 7,
    essential: true
  });
}

export function SeismicMap({ events }: SeismicMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const isMapLoadedRef = useRef(false);
  const lastFlyToEventRef = useRef<string | null>(null);
  const eventsRef = useRef<Earthquake[]>(events);
  const featureCollectionRef = useRef(toFeatureCollection(events));
  const showHeatmapRef = useRef(false);
  const showProvinceBordersRef = useRef(false);

  const selectedEvent = useDashboardStore((state) => state.selectedEvent);
  const minMagnitude = useDashboardStore((state) => state.filters.minMagnitude);
  const setMinMagnitude = useDashboardStore((state) => state.setMinMagnitude);
  const selectEvent = useDashboardStore((state) => state.selectEvent);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showProvinceBorders, setShowProvinceBorders] = useState(false);
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

  const filteredEvents = useMemo(
    () => events.filter((event) => event.magnitude >= minMagnitude),
    [events, minMagnitude]
  );
  const featureCollection = useMemo(() => toFeatureCollection(filteredEvents), [filteredEvents]);
  const latestEvent = useMemo(() => newestEvent(filteredEvents), [filteredEvents]);
  const plottedEventLabel = `${filteredEvents.length} plotted ${filteredEvents.length === 1 ? "event" : "events"}`;

  useEffect(() => {
    eventsRef.current = filteredEvents;
    featureCollectionRef.current = featureCollection;
  }, [featureCollection, filteredEvents]);

  useEffect(() => {
    showHeatmapRef.current = showHeatmap;
  }, [showHeatmap]);

  useEffect(() => {
    showProvinceBordersRef.current = showProvinceBorders;
  }, [showProvinceBorders]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current || !mapboxToken) {
      return;
    }

    mapboxgl.accessToken = mapboxToken;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: PHILIPPINES_CENTER,
      zoom: DEFAULT_ZOOM,
      minZoom: 3.8,
      maxBounds: [
        [114.0, 3.5],
        [129.5, 22.5]
      ]
    });

    mapRef.current = map;
    map.addControl(new mapboxgl.NavigationControl(), "top-right");

    map.on("load", () => {
      isMapLoadedRef.current = true;
      map.addSource("earthquakes", {
        type: "geojson",
        data: featureCollectionRef.current,
        cluster: true,
        clusterRadius: 42,
        clusterMaxZoom: 8
      });
      map.addSource("province-boundaries", {
        type: "geojson",
        data: "/data/provinces.geojson"
      });

      map.addLayer({
        id: "province-fill",
        type: "fill",
        source: "province-boundaries",
        paint: {
          "fill-color": "#38bdf8",
          "fill-opacity": 0.04
        },
        layout: { visibility: "none" }
      });
      map.addLayer({
        id: "province-lines",
        type: "line",
        source: "province-boundaries",
        paint: {
          "line-color": "#67e8f9",
          "line-opacity": 0.42,
          "line-width": 0.8
        },
        layout: { visibility: "none" }
      });
      map.addLayer({
        id: "earthquake-heat",
        type: "heatmap",
        source: "earthquakes",
        maxzoom: 9,
        paint: {
          "heatmap-weight": ["interpolate", ["linear"], ["get", "magnitude"], 0, 0, 7, 1],
          "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 4, 0.8, 9, 2.2],
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(8,47,73,0)",
            0.25,
            "#22d3ee",
            0.5,
            "#facc15",
            0.75,
            "#fb923c",
            1,
            "#ef4444"
          ],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 4, 14, 9, 34],
          "heatmap-opacity": 0.75
        },
        layout: { visibility: "none" }
      });
      map.addLayer({
        id: "earthquake-clusters",
        type: "circle",
        source: "earthquakes",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": ["step", ["get", "point_count"], "#22d3ee", 8, "#facc15", 18, "#fb7185"],
          "circle-radius": ["step", ["get", "point_count"], 17, 8, 23, 18, 30],
          "circle-opacity": 0.82,
          "circle-stroke-color": "#f8fafc",
          "circle-stroke-width": 1
        }
      });
      map.addLayer({
        id: "earthquake-cluster-count",
        type: "symbol",
        source: "earthquakes",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
          "text-size": 12
        },
        paint: { "text-color": "#020617" }
      });
      map.addLayer({
        id: "earthquake-points",
        type: "circle",
        source: "earthquakes",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": [
            "step",
            ["get", "magnitude"],
            "#22c55e",
            4,
            "#facc15",
            5,
            "#fb923c",
            6,
            "#ef4444"
          ],
          "circle-radius": ["interpolate", ["linear"], ["get", "magnitude"], 1, 5, 7, 17],
          "circle-opacity": 0.9,
          "circle-stroke-color": "#f8fafc",
          "circle-stroke-width": 1.4
        }
      });
      map.addLayer({
        id: "earthquake-pulse",
        type: "circle",
        source: "earthquakes",
        filter: ["==", ["get", "id"], latestEvent?.id ?? ""],
        paint: {
          "circle-color": "#ffffff",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 16, 9, 34],
          "circle-opacity": 0.16,
          "circle-stroke-color": "#67e8f9",
          "circle-stroke-opacity": 0.75,
          "circle-stroke-width": 2
        }
      });

      map.on("click", "earthquake-points", (event: mapboxgl.MapLayerMouseEvent) => {
        const feature = event.features?.[0] as EarthquakeFeature | undefined;
        const eventId = feature?.properties?.id;
        const matchingEvent = eventsRef.current.find((item) => item.id === eventId);
        if (matchingEvent) {
          selectEvent(matchingEvent);
        }
      });

      map.setLayoutProperty("earthquake-heat", "visibility", showHeatmapRef.current ? "visible" : "none");
      map.setLayoutProperty("province-fill", "visibility", showProvinceBordersRef.current ? "visible" : "none");
      map.setLayoutProperty("province-lines", "visibility", showProvinceBordersRef.current ? "visible" : "none");
      flyToSignificantEvent(map, newestEvent(eventsRef.current), lastFlyToEventRef);
    });

    return () => {
      isMapLoadedRef.current = false;
      map.remove();
      mapRef.current = null;
    };
  }, [latestEvent?.id, mapboxToken, selectEvent]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapLoadedRef.current) {
      return;
    }

    const source = map.getSource("earthquakes") as mapboxgl.GeoJSONSource | undefined;
    source?.setData(featureCollection);

    if (map.getLayer("earthquake-pulse")) {
      map.setFilter("earthquake-pulse", ["==", ["get", "id"], latestEvent?.id ?? ""]);
    }
  }, [featureCollection, latestEvent?.id]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapLoadedRef.current || !map.getLayer("earthquake-heat")) {
      return;
    }

    map.setLayoutProperty("earthquake-heat", "visibility", showHeatmap ? "visible" : "none");
  }, [showHeatmap]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapLoadedRef.current) {
      return;
    }

    const visibility = showProvinceBorders ? "visible" : "none";
    if (map.getLayer("province-fill")) {
      map.setLayoutProperty("province-fill", "visibility", visibility);
    }
    if (map.getLayer("province-lines")) {
      map.setLayoutProperty("province-lines", "visibility", visibility);
    }
  }, [showProvinceBorders]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapLoadedRef.current) {
      return;
    }
    flyToSignificantEvent(map, latestEvent, lastFlyToEventRef);
  }, [latestEvent]);

  function resetView() {
    mapRef.current?.flyTo({
      center: PHILIPPINES_CENTER,
      zoom: DEFAULT_ZOOM,
      essential: true
    });
  }

  return (
    <div className="min-h-[560px] rounded-md border border-border bg-surface p-4 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <MapPinned aria-hidden className="h-4 w-4 text-cyan-300" />
          <div>
            <h2 className="text-sm font-semibold">Operations map</h2>
            <p className="text-xs text-muted">{plottedEventLabel}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            aria-label="Toggle heatmap"
            aria-pressed={showHeatmap}
            title="Toggle heatmap"
            onClick={() => setShowHeatmap((value) => !value)}
            className={`grid h-9 w-9 place-items-center rounded-md border ${
              showHeatmap ? "border-orange-300/60 bg-orange-300/15 text-orange-100" : "border-border bg-background text-muted"
            }`}
          >
            <Flame aria-hidden className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label="Toggle province borders"
            aria-pressed={showProvinceBorders}
            title="Toggle province borders"
            onClick={() => setShowProvinceBorders((value) => !value)}
            className={`grid h-9 w-9 place-items-center rounded-md border ${
              showProvinceBorders ? "border-cyan-300/60 bg-cyan-300/15 text-cyan-100" : "border-border bg-background text-muted"
            }`}
          >
            <Layers aria-hidden className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label="Reset map view"
            title="Reset map view"
            onClick={resetView}
            className="grid h-9 w-9 place-items-center rounded-md border border-border bg-background text-muted"
          >
            <RotateCcw aria-hidden className="h-4 w-4" />
          </button>
          <label className="flex h-9 items-center gap-2 rounded-md border border-border bg-background px-3 text-xs text-muted">
            M{minMagnitude.toFixed(1)}+
            <input
              aria-label="Minimum magnitude"
              type="range"
              min="0"
              max="7"
              step="0.5"
              value={minMagnitude}
              onChange={(event) => setMinMagnitude(Number(event.target.value))}
              className="h-1 w-28 accent-cyan-300"
            />
          </label>
        </div>
      </div>

      <div className="relative mt-4 min-h-[430px] overflow-hidden rounded-md border border-slate-700/70 bg-slate-950">
        <div ref={containerRef} data-testid="mapbox-container" className="absolute inset-0" />
        {!mapboxToken && (
          <div className="absolute inset-0 grid place-items-center bg-slate-950/90 px-6 text-center">
            <div>
              <Crosshair aria-hidden className="mx-auto h-10 w-10 text-cyan-200" />
              <p className="mt-3 text-sm font-medium text-slate-100">Mapbox token required</p>
              <p className="mt-1 text-xs text-muted">Set NEXT_PUBLIC_MAPBOX_TOKEN to render live map tiles.</p>
            </div>
          </div>
        )}
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border border-border bg-slate-950/80 px-3 py-2 backdrop-blur">
          <p className="text-xs font-semibold text-slate-100">Magnitude legend</p>
          <div className="mt-2 flex items-center gap-3 text-[11px] text-muted">
            <span className="inline-flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              M&lt;4
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-yellow-300" />
              M4
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-orange-400" />
              M5
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
              M6+
            </span>
          </div>
        </div>
      </div>

      <p className="mt-3 text-xs text-muted">
        {selectedEvent
          ? `${formatMagnitude(selectedEvent.magnitude)} - ${selectedEvent.province ?? selectedEvent.place} - ${formatDepth(selectedEvent.depth_km)}`
          : latestEvent
            ? `Newest plotted: ${formatMagnitude(latestEvent.magnitude)} near ${latestEvent.province ?? latestEvent.place}`
            : "No events match the current map filter"}
      </p>
    </div>
  );
}
