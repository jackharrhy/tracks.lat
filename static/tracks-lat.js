import * as L from "/static/leaflet-src.esm.js";

document.addEventListener("DOMContentLoaded", (event) => {
  fetch("?format=json")
    .then(async (response) => {
      const data = await response.json();
      console.log({ data });

      const layers = [];

      const features = [];

      data.tracks.map(({ geometry: geometryString }) => {
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

        layers.push(layer);
      });

      const center = JSON.parse(data.aggregates.center).coordinates;
      center.reverse();

      const extent = JSON.parse(data.aggregates.extent);

      const map = L.map("map")
        .setView(center, 10)
        .fitBounds([
          [extent.coordinates[0][0][1], extent.coordinates[0][0][0]],
          [extent.coordinates[0][2][1], extent.coordinates[0][2][0]],
        ]);

      window.map = map;

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);

      layers.map((layer) => {
        layer.addTo(map);
      });
    })
    .catch((error) => {
      console.error("Error:", error);
    });
});

console.log("tracks.lat/lon 🌐");
