# Exemple de Quiz: Les Promises en JavaScript

## Format Interactif (Question par Question)

---

## Question 1 (Vrai/Faux)

Une Promise peut être dans plusieurs états en même temps.

**Ta réponse ?**

---

**Réponse:** Faux

**Explication:** Une Promise ne peut être que dans un seul état à la fois: pending, fulfilled, ou rejected.

---

## Question 2 (QCM)

Quel mot-clé utilise-t-on pour résoudre une Promise ?

A) `complete`
B) `resolve`
C) `finish`
D) `success`

**Ta réponse ?**

---

**Réponse:** B) `resolve`

**Explication:** `resolve()` est la fonction appelée quand la Promise réussit.

---

## Question 3 (Question Ouverte)

Quelle est la différence entre `.then()` et `.catch()` ?

**Ta réponse ?**

---

**Réponse attendue:** `.then()` traite le cas de succès (fulfilled) tandis que `.catch()` traite le cas d'erreur (rejected).

---

## Question 4 (Exercice)

Complète le code:

```javascript
new Promise((resolve, reject) => {
  // Si condition est vraie, ______("OK")
  // Sinon, ______("Erreur")
});
```

**Ta réponse ?**

---

**Réponse:** `resolve("OK")` et `reject("Erreur")`

---

## Question 5 (Vrai/Faux)

`async/await` est une syntaxe plus moderne que `.then()/.catch()`.

**Ta réponse ?**

---

**Réponse:** Vrai

**Explication:** `async/await` a été introduit en ES2017 pour simplifier la lecture du code asynchrone.

---

## Question 6 (QCM)

Que retourne une fonction `async` ?

A) Une valeur normale
B) Une Promise
C) Un callback
D) Un objet

**Ta réponse ?**

---

**Réponse:** B) Une Promise

**Explication:** Toute fonction déclarée avec `async` retourne automatiquement une Promise.

---

## Question 7 (Question Ouverte)

À quoi sert `.finally()` ?

**Ta réponse ?**

---

**Réponse attendue:** `.finally()` exécute du code après la Promise, que ce soit en cas de succès ou d'échec.

---

## Question 8 (Exercice)

Quel est l'équivalent async/await de ce code ?

```javascript
getData().then(d => console.log(d)).catch(e => console.error(e));
```

**Ta réponse ?**

---

**Réponse:**

```javascript
async function() {
  try {
    const d = await getData();
    console.log(d);
  } catch (e) {
    console.error(e);
  }
}
```

---

## Question 9 (Vrai/Faux)

Une Promise une fois fulfilled ou rejected peut changer d'état.

**Ta réponse ?**

---

**Réponse:** Faux

**Explication:** Une Promise est "immuable" une fois dans un état final (fulfilled ou rejected). C'est ce qu'on appelle "settled".

---

## Question 10 (Question Ouverte)

Pourquoi utiliser les Promises au lieu des callbacks ?

**Ta réponse ?**

---

**Réponse attendue:**
- Meilleure lisibilité (évite le callback hell)
- Chaînage plus facile avec `.then()`
- Gestion d'erreurs centralisée avec `.catch()`
- Syntaxe moderne avec async/await

---

## 📊 Bilan Final

Après les 10 questions:
- **Score:** X/10
- **Points forts:** [Les concepts bien compris]
- **À revoir:** [Les concepts à approfondir]
- **Prochaine étape:** [Nouveau sujet ou approfondissement]
