const fs = require("fs");
const args = process.argv; 

fs.readFile("./javascript_blueprint.json", "utf8", (err, jsonString) => {
  if (err) {
    console.log("File read failed:", err);
    return;
  }
  console.time("parsing json string");

  JSON.parse(jsonString)
  console.timeLog("parsing json string");

  console.time("getting proximityDictionary");

getProximityDictionary(  JSON.parse(jsonString),parseInt(args[2]))

  console.timeLog("getting proximityDictionary");


  console.time("reticulating splines");

  fs.writeFile('proximity_dictionary.json', JSON.stringify(getProximityDictionary(  JSON.parse(jsonString),parseInt(args[2]))), 'utf8',  ()=>{})
console.timeLog("reticulating splines");

});

function getProximityDictionary(blueprint, numberOfNeighbors) {
  const poleLocationDictionary = {};
  for (let i = 0; i < blueprint.blueprint.entities.length; i++) {
    const entity = blueprint.blueprint.entities[i];
    if (entity.name === "big-electric-pole") {
      poleLocationDictionary[entity.entity_number] = [entity.position.x, entity.position.y];
    }
  }

  const proximityDictionary = {};
  for (const entityNumber in poleLocationDictionary) {
    const fiveMinimalDistances = [];
    const fiveMinimalIndices = [];
    const dictionaryOfDistances = {};
    for (const otherEntityNumber in poleLocationDictionary) {
      const pt1 = poleLocationDictionary[entityNumber];
      const pt2 = poleLocationDictionary[otherEntityNumber];
      const dist = getEuclideanDistance(pt1, pt2);
      if (dist <= 100) {
        dictionaryOfDistances[otherEntityNumber] = dist;
      }
    }
    const sortedDistances = Object.entries(dictionaryOfDistances).sort((a, b) => a[1] - b[1]);
    const fiveClosestPoints = sortedDistances.slice(1, numberOfNeighbors + 1).map(([key]) => parseInt(key));
    proximityDictionary[entityNumber] = fiveClosestPoints;
  }

  return proximityDictionary;
}

function getEuclideanDistance(pt1, pt2) {
  const dx = pt1[0] - pt2[0];
  const dy = pt1[1] - pt2[1];
  return Math.sqrt(dx * dx + dy * dy);
}

