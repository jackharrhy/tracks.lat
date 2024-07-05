import * as L from "/static/leaflet-src.esm.js";

let map;

const setup = async () => {
  if (map) {
    throw new Error("Map already initialized");
  }

  const response = await fetch("?format=json");
  const data = await response.json();
  console.log({ data });

  const tracks = [];
  const features = [];

  data.tracks.map(({ geometry: geometryString, slug, username }) => {
    const geometry = JSON.parse(geometryString);
    features.push(geometry);

    const layer = L.geoJSON(geometry, {
      style: (feature) => {
        return {
          color: "red",
        };
      },
    }).bindPopup((layer) => {
      return "foo";
    });

    tracks.push({
      layer,
      slug,
      username,
    });
  });

  const center = JSON.parse(data.aggregates.center).coordinates;
  center.reverse();

  const extent = JSON.parse(data.aggregates.extent);

  map = L.map("map")
    .setView(center, 10)
    .fitBounds([
      [extent.coordinates[0][0][1], extent.coordinates[0][0][0]],
      [extent.coordinates[0][2][1], extent.coordinates[0][2][0]],
    ]);

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  tracks.map(({ layer }) => {
    layer.addTo(map);
  });

  Array.from(document.querySelectorAll("a[data-track]")).map((elm) => {
    const { trackUsername, trackSlug } = elm.dataset;

    const zoomToTrack = () => {
      const track = tracks.find(
        ({ username, slug }) => username === trackUsername && slug === trackSlug
      );

      if (!track) {
        console.error("Track not found");
        return;
      }

      map.flyToBounds(track.layer.getBounds());
    };

    elm.addEventListener("mouseover", (event) => {
      zoomToTrack();
    });

    elm.addEventListener("focus", (event) => {
      zoomToTrack();
    });
  });
};

document.addEventListener("DOMContentLoaded", () => {
  if (!document.querySelector("#map")) {
    return;
  }
  setup();
});

window.addEventListener("htmx:afterSwap", () => {
  if (!document.querySelector("#map")) {
    if (map) {
      map.remove();
      map = undefined;
    }

    return;
  }

  setup();
});

console.log("tracks.lat/lon 🌐");
