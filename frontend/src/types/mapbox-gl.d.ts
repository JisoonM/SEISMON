declare module "mapbox-gl" {
  namespace mapboxgl {
    let accessToken: string;

    type LngLatLike = [number, number];

    interface MapOptions {
      center: LngLatLike;
      container: HTMLElement;
      maxBounds?: [LngLatLike, LngLatLike];
      minZoom?: number;
      style: string;
      zoom: number;
    }

    interface FlyToOptions {
      center: LngLatLike;
      essential?: boolean;
      zoom: number;
    }

    interface GeoJSONSource {
      setData(data: GeoJSON.GeoJSON): this;
    }

    interface MapLayerMouseEvent {
      features?: Array<GeoJSON.Feature<GeoJSON.Geometry, Record<string, unknown>>>;
    }

    class Map {
      constructor(options: MapOptions);
      addControl(control: NavigationControl, position?: string): this;
      addLayer(layer: Record<string, unknown>): this;
      addSource(id: string, source: Record<string, unknown>): this;
      flyTo(options: FlyToOptions): this;
      getLayer(id: string): unknown;
      getSource(id: string): GeoJSONSource | undefined;
      on(event: "load", handler: () => void): this;
      on(event: "click", layerId: string, handler: (event: MapLayerMouseEvent) => void): this;
      remove(): void;
      setFilter(layerId: string, filter: unknown[]): this;
      setLayoutProperty(layerId: string, name: string, value: unknown): this;
    }

    class NavigationControl {
      constructor(options?: Record<string, unknown>);
    }
  }

  export default mapboxgl;
}
