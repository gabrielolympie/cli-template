# Exemple de Cours: Les Promises en JavaScript

## 🎯 Objectifs d'Apprentissage

À la fin de ce cours, tu seras capable de:
- Comprendre ce qu'est une Promise
- Créer et manipuler des Promises
- Gérer les erreurs avec `.catch()`
- Utiliser `async/await`

## 📖 Introduction

Une **Promise** est un objet JavaScript qui représente l'achèvement (ou l'échec) d'une opération asynchrone.

### Pourquoi les Promises ?

Avant les Promises, on utilisait des **callbacks**, ce qui menait au "callback hell":

```javascript
// Callback hell - à éviter !
getData(function(a) {
  getMoreData(a, function(b) {
    getEvenMoreData(b, function(c) {
      // ...
    });
  });
});
```

## 🔑 Concepts Clés

### Les 3 États d'une Promise

1. **Pending** (en attente): État initial
2. **Fulfilled** (réussie): L'opération a réussi
3. **Rejected** (échouée): L'opération a échoué

### Création d'une Promise

```javascript
const maPromise = new Promise((resolve, reject) => {
  const succes = true; // condition
  
  if (succes) {
    resolve("L'opération a réussi !");
  } else {
    reject("L'opération a échoué !");
  }
});
```

## 💡 Exemples Concrets

### Exemple 1: Simulation d'API

```javascript
function fetchData() {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const data = { id: 1, name: "Exemple" };
      resolve(data);
    }, 1000);
  });
}

fetchData().then(data => console.log(data));
```

### Exemple 2: Gestion d'Erreurs

```javascript
fetchData()
  .then(data => {
    console.log("Données reçues:", data);
  })
  .catch(error => {
    console.error("Erreur:", error);
  })
  .finally(() => {
    console.log("Opération terminée");
  });
```

## ⚡ async/await

Syntaxe moderne pour travailler avec les Promises:

```javascript
async function getData() {
  try {
    const data = await fetchData();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}
```

## 📝 Points à Retenir

- **Promise** = objet pour opérations asynchrones
- **resolve()** = succès
- **reject()** = échec
- **`.then()`** = traite le succès
- **`.catch()`** = traite l'échec
- **async/await** = syntaxe moderne plus lisible

## 🔄 Prochaine Étape

Prêt pour le quiz de 10 questions pour vérifier ta compréhension ?
