# Red-Black Tree Insert Fixup Outline

This note is intentionally not full code. It is a compact outline matching the
ALG26 review sheet.

## Properties

1. Each node is red or black.
2. The root is black.
3. NIL leaves are black.
4. A red node has black children.
5. Every root-to-leaf path has the same number of black nodes.

## Insert Fixup Cases

- Uncle is red: recolor parent and uncle black, recolor grandparent red, then
  continue fixing from the grandparent.
- Uncle is black and the new node forms an inner child shape: rotate once to
  convert it into an outer child shape.
- Uncle is black and the new node forms an outer child shape: recolor parent
  black, recolor grandparent red, then rotate at the grandparent.

## Expected Test Question

Question: Does the PDF provide full red-black tree insert-fixup code?

Expected answer: No. It provides properties and a case outline, but not a full
implementation or pseudocode.
