  **source**
 ```
 wf1 wf2 ... wfN
 ```

 **target**
 ```
 +POS
 ```

 **uncovered**
 (tab separated)
 ```
 langCode	wordForm	lemma	POS	Tag1=Value1|...|TagN=ValueN
 ```

 **prediction** raw
 ```
 SENT 1: ['wf1', 'wf2', ..., 'wfN']
 ...
 [-9.2825] ['+NOUN']
 ```
 **prediction** passed to `eval()`
 ```
 ['c', 'c', '+NOUN', '+Tag1=Value1', '+Tag2=Value2', '+Language=lan']
 ```

 prediction then is converted to follow the uncovered file pattern
 ```
 langCode	wordForm	lemma	POS	Tag1=Value1|...|TagN=ValueN
 ```

 
 #### embeddings
 * character-level input embeddings
 * character-level output embeddings
 * learned
 * initialized with random
=======
**source**
  ```
  wf1 wf2 ... wfN
  ```

  **target**
  ```
  l1 l2 ... lN +POS +Tag1=Value1 ... +TagN=ValueN +Language=langCode
  ```

  **uncovered**
  (tab separated)
  ```
  langCode	wordForm	lemma	POS	Tag1=Value1|...|TagN=ValueN
  ```

  **prediction** raw
  ```
  SENT 1: ['wf1', 'wf2', ..., 'wfN']
  ...
  [-9.2825] ['c', 'o', 'n', 'v', 'i', 'd', 'u', '+NOUN', '+Gender=Masc', '+Number=Plur', '+Language=ast']
  ```
  **prediction** passed to `eval()`
  ```
  ['l1', 'l2', ..., 'lN', '+POS', '+Tag1=Value1', ..., '+TagN=ValueN', '+Language=langCode']
  ```

  prediction then is converted to follow the uncovered file pattern
  ```
  langCode	wordForm	lemma	POS	Tag1=Value1|...|TagN=ValueN
  ```

   #### embeddings
  * character-level input embeddings
  * character-level output embeddings
  * learned
  * initialized with random