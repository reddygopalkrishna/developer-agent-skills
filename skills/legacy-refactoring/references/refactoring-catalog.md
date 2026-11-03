# Refactoring catalog

Common behavior-preserving refactorings, each with when to use it, the safe mechanics, and the usual trap. Run the tests after each one. Names follow Martin Fowler's *Refactoring* catalog.

## Extract function

- **When:** a block of code needs a comment to explain what it does, or is duplicated, or makes a function too long to follow.
- **Steps:** create a new function named for *what* the block does; move the block in; pass in the variables it reads; return the values it changes; replace the block with a call.
- **Trap:** the block assigns to several outer variables. Return a small result object, or extract a smaller piece first.

## Inline function / inline variable

- **When:** the body is as clear as the name, or an indirection adds nothing.
- **Steps:** check the function is not polymorphic (overridden) and has no other callers you would miss; replace each call with the body; delete the function.
- **Trap:** inlining something called through reflection, configuration or an interface.

## Rename (variable, function, class, file)

- **When:** the name does not say what the thing does or holds.
- **Steps:** use the editor's rename refactoring so every reference changes; for public APIs, add the new name and deprecate the old one first (parallel change).
- **Trap:** names used as strings: serialization keys, database columns, routes, dependency-injection registrations, logs that dashboards parse.

## Move function / move field

- **When:** a function uses another module's data more than its own.
- **Steps:** copy it to the target; make the old one delegate to the new one; move callers; delete the old one.
- **Trap:** circular imports. Move the shared dependency first, or introduce an interface.

## Extract class / extract module

- **When:** one class has several groups of fields and methods that change for different reasons.
- **Steps:** create the new class; move fields one at a time, then the methods that use them; keep the old class delegating until callers move.
- **Trap:** splitting by technical layer ("helpers", "utils") instead of by responsibility.

## Introduce parameter object

- **When:** the same group of parameters travels together (`startDate, endDate`, `street, city, postcode`).
- **Steps:** create a small immutable type; add it as a new parameter; move callers; remove the individual parameters. Then move behavior that belongs to the group onto the new type.
- **Trap:** a parameter object that grows into a bag of unrelated options.

## Replace magic literal with named constant

- **When:** a number or string has meaning that is not obvious (`86400`, `"PENDING"`).
- **Steps:** create a named constant or enum; replace each occurrence *that has the same meaning* (not every `0` or `1`).
- **Trap:** replacing literals that happen to have the same value but different meanings.

## Replace nested conditionals with guard clauses

- **When:** deep nesting where special cases wrap the main path.
- **Steps:** turn each special case into an early `return`/`throw` at the top; leave the normal path un-nested at the end.
- **Trap:** changing the order of checks changes behavior when conditions overlap. Keep the original order.

## Decompose conditional

- **When:** a complex condition or its branches are hard to read.
- **Steps:** extract the condition into a well-named function (`isEligibleForRefund(order)`), and each branch into its own function if large.

## Replace conditional with polymorphism

- **When:** the same `switch`/`if` on a type code appears in several places.
- **Steps:** create a type per case implementing a common interface; move each branch into its type; replace the conditional with a call on the interface. Do it one method at a time.
- **Trap:** using it for a single, stable switch; a plain conditional or a lookup table is often clearer.

## Split loop

- **When:** one loop does two unrelated things.
- **Steps:** duplicate the loop; remove one responsibility from each copy; then extract each loop into a function if useful.
- **Trap:** the two parts depend on each other's intermediate state. Performance cost is usually negligible; measure if in doubt.

## Replace loop with pipeline

- **When:** a loop filters, maps and accumulates in a way a collection pipeline expresses more clearly (`filter`/`map`, LINQ, streams, comprehensions).
- **Trap:** pipelines with side effects, or lazy evaluation changing when side effects happen.

## Separate query from modifier

- **When:** a function both returns a value and changes state, so callers cannot ask without changing things.
- **Steps:** create a pure query function; make the original call it and keep its side effect; move callers that only need the value to the query.

## Encapsulate field / encapsulate collection

- **When:** many places mutate a field or collection directly, so invariants cannot be enforced.
- **Steps:** add accessor methods; route all access through them; for collections, return a read-only view or copy and add explicit `add`/`remove` methods.

## Replace temp with query

- **When:** a temporary variable holds a value that could be computed by a clearly named function, which also makes extraction easier.
- **Trap:** the computation is expensive or has side effects.

## Change function declaration (signature)

- **When:** parameters or the name need to change.
- **Steps (simple):** use the editor refactoring if all callers are in the codebase.
- **Steps (migration):** add the new function, make the old one call it, move callers over, then delete the old function (parallel change). Use this for public APIs or many callers.

## Substitute algorithm

- **When:** a clearer or faster algorithm produces the same results.
- **Steps:** make sure characterization tests cover the full range of inputs (consider a property-based test comparing old and new implementations on random inputs), then swap.
- **Trap:** subtle differences in ordering, rounding, error cases or performance characteristics.

## Order of operations for a tangled function

A sequence that usually works on a large legacy function:

1. Characterization tests around the function's public behavior.
2. Rename local variables so you can read it.
3. Guard clauses to flatten nesting.
4. Extract function for each coherent block.
5. Move extracted functions to the class or module where their data lives.
6. Introduce parameter objects for argument groups that now stand out.
7. Only then make the behavior change you came for.
