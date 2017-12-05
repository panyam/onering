
Onering Language Specification
==============================

Onering is an attempt at making schema specifications and transformations easy.

Modules
-------

A Onering program is a collection of (possibly) distributed modules.   Modules are logical constructs divorced from any physical storage concerns and are the way to control name spaces and enabling groupings and organizations in large programs.  Modules are flexible and mutable in that modules can be extended by seperate libraries across programs (as long as they are loaded within the same runtime).  Modules have fully qualified names and can be declared within other modules (with the FQNs simply aggregating).

For example:

```
module a.b.A {
}
```

is same as

```
module a {
    module b.A {
    }
}
```

### Declarations

Each module contains declarations.   Declarations define types, constant variables, macros and so on.  Declarations are the way to bind an expression to a variable that is accessible through out the runtime.

Expressions
-----------

Everything in onering is an expression.  Expressions are also first class objects and can be passed (similar to Quotes in Lisp) to other values by simply constructing one.  This gives us lazy evalations for free.

Expressions comprise of:

* literals
* compound expressions
* function abstractions (definitions)
* function application (function calls)
* type declarations
* variables
* and more

### Literals

Literals are actual values for expressions.  These can be boolean values (true, false), strings (single or multi line), numerical values (ints, longs, floats, doubles, imaginary).

### Compound Expressions

Compound expression represent various collections of expressions.  eg lists, tuples, expression lists and so on.

eg:

Expression Blocks: ``` { expr1 ; expr2 ... ; exprn } ```

Lists: ``` [1, 2, 3] ```

Tuples:  ``` ( 1, 2, 3 ) ```

Dictionaries:  ``` { "a" : 1, "b" : 2, "c" : 3 } ```

## Types

Onering is a strongly typed DSL.   Types are first class expressions and as such can be passed around to as function parameters either for evaluation or for creating other types.  The five main concepts in types are:

* **Atomic Types**: These are basic named types like int, bool, char etc.
* **Container types**: These allow entities and related objects to be grouped into a single type, eg unions, records, enums.
* **Type Operators**: Type function that enable functions over types such as generics.
* **Type Applications**: Type applications are the specialization of a parametrized type, eg Pair<int, bool>.
* **Type Traits/Classes**: Type classes that allow polymorphic overloading.

### Atomic Types

Onering has very few builtin types.  Basic leaf types like ints, bools, chars, floats belong to the Atomic type families.  These denote types of actual basic values.

### Container Types

#### Records

Records, like tuples are product types but each of its element is labelled.   A record is analogous to a struct in other languages.  Record grammer is defined by:


For example:

```
module test {
    record Person {
        age : int
        name : string
        extrovert : boolean ?
        active : boolean = true
        address : record Address {
            suite : string ?
            number : string
            street : string
            suburb : string
            country : string
        }
    }
}
```

Note that inner types inherit the FQN of the parent in which it is defined.  Hence Address would be fully qualified as "test.Person.Address and treated as an independent record.   Also inner types MUST be named. 

Records can also be parametrized, eg:

```
record Pair <A,B> {
    first : A
    second : B
}
```

#### Unions

Unions are discriminated variant (sum) types and can be labelled.  Unions can be defined as:

Like Records, Union types can also be parametrized, eg:

```
union MyUnion <A,B> {
    addresses : list<A>
    places : array<B>
}
```

#### Enums

Enums are a more specialized form of unions where the type of each option is same as the union itself:

All values associated with enum options must be of the same type.  The literal value is ONLY used for construction of an enum and not to determine the "type" of the enum itself.

For example with the following enum:

```
enum Color {
    red = 0xff0000
    green = 0x00ff00
    blue = 0x0000ff
}
```

there are a couple of things to note:

* red, green and blue can ONLY be referred to by Color.red, Color.green and Color.blue respectively.
* The types of red, green and blue are "Color" and NOT int as their literal value would suggest.
* The literal values are for runtime construction, eg `x = makeenum(Color, 0xff0000)` (or some variant of this).
* The final point is powerful since this way enums can be extended for new values and they would would Color as their type, eg:
```
black = makeenum(Color, 0x000000)
````

#### Type Aliases

Types can be given aliases or other names, eg:

```
alias Age = int
alias IntMap<V> = map<int, V>
alias StringMap<V> = map<string, V>
```

## Function Definitions and Declarations

A function has two components:

* A signature
* Its body

The Signature of a function determines parametrization of the function (resulting in quantifiers) as well as in determining the type of inputs and output of the function.

The signature of a function is optional, at which point it *can* be inferred if there are no difficulties in doing so.   An example of an annotated function is:

```
fun add(a, b) : int -> int -> int {
    ...
}
```

Alternatively a type's signature can be intermingled with the parameters with:

```
fun add(a : int, b : int) -> c {
    ...
}
```

The above are similar and the choice of both are a matter of readability.

Things are more interesting when parameterization comes into play:

```
fun add <A> (a : A, b : A) -> A {
    ...
}
```

or 

```
fun add <A> (a, b) : A -> A -> A {
    ...
}
```

The usual rules around type parameter constraints apply.

Some more examples include:

```
# Mixing params and fun sig
fun map <A,B> (a : list<A>, b : A -> B) -> list<B>

# Partial seperation of sig and def - 1 
fun map <A,B> (a, b) : (list<A>, A -> B) -> list<B>

# Partial seperation of sig and def - 2
fun map <A,B>(a, b) : list<A> -> (A -> B) -> list<B>
```

### Traits

Now the above are good for almost all cases of quantifications.  How would type classes work with this?  Eg we had a Numeric type class any of the above would be good:

```
# Plain option
trait Numeric<T> {
    fun iszero(t : T) -> boolean
    fun succ(t : T) -> T
    fun pred(t : T) -> T
}

# with funtypes:
trait Numeric<T> {
    funtype iszero : T -> boolean
    funtype succ : T -> T
    funtype pred : T -> T

    # Option 2
    funtype iszero : (T) -> boolean
    funtype succ : (T) -> T
    funtype pred : (T) -> T
}

# with sig and def seperation:
trait Numeric<T> {
    fun iszero : T -> boolean
    fun succ : T -> T
    fun pred : T -> T

    # Option 2
    fun iszero : (T) -> boolean
    fun succ : T -> T
    fun pred : T -> T
}
```

Note in the above, the functions inside the traits (or type classes) did not require the type params "T" as it is implicitly added to ALL functions for a trait to parametrize it over.

Now that we have traits (ie type classes) how can we define specific classes of it?  eg if we want a Numeric<int> vs a Numeric<Complex> how would that work?

```
instance Numeric<int> {
    fun iszero(x) { equals(x, 0) }
    fun succ(x) { sum(x, 1) }
    fun pred(x) { subtract(x, 1) }
}

instance Numeric<Complex> {
    fun iszero(x) { and(equals(x.real, 0), equals(x.img, 0)) }
    fun succ(x) { Complex(sum(x.real + 1), x.img) }
    fun pred(x) { Complex(subtract(x.real + 1), x.img) }
}
```

Thanks to type classes we actually dont need function overloading.  In the function overloading world we would have done:

```
fun <A>add(a : A, b : A) -> A

// or
fun add(a,b) : <A> A -> A -> A
fun add(a,b) : <A> (A, A) -> A
```

and then proceed to multiple implementations:

```
funi <int>add(a, b) {
    // int version of add
}

funi <double>add(a, b) {
    // double version of add
}
```

But the same can be achieved with:

```
trait Addable<A> {
    fun add : (A, A) -> A

    // or 
    fun add : A -> A -> A
}
```

followed by instances of:

```
instance Addable<int> {
    fun add(a,b) {
        ...
    }
}

instance Addable<Complex> {
    fun add(a,b) {
        ...
    }
}
```

Alternatively a shorthand for above could be:

```
funi <int> add(a,b) { ... }
funi <double> add(a,b) { ... }
```

#### Currying with typeclasses

Say if we had:

```
trait Map<K,V> {
    fun somefun(k,v) : K -> V -> map<K,V>
    ...
}
```

If we wanted an map with int keys and a map with string keys, we want something like:

```
trait IntMap<V> = Map<Int, V>
trait StringMap<V> = Map<string, V>
```

How will this work? - TBD

### Variable Declarations

Onering has a very simple grammar that strives to be parseable with a LL(k) parser.  

Operators 

1. Call by value, reference, name and need to be supported
2. Functions as first class citizens (including currying)
3. Types as first class citizens and functions over types (type reification and ignoring) - ie "extends" as a type function
4. Reflection from day 1
5. Tooling from day 1
6. Paradigm agnostic programming!  How do we do array programming?  How do we enable vectorization?  How do we something optimized for streams?  How do enable IO?
7. Laziness

Why is (6) important?   Consider the following examples:

1. Matrix multiplications
2. Handling IO
3. Arrays/Dictionaries
4. Exceptions

These are all really "custom" behaviours that can be modelled over expressions/flows/types.

For example a N dimentional matrix where each element is of type T, can be defined via type classes as:

```
type <T> Matrix :
    zero_matrix :: () -> Matrix<T>
    diag_matrix :: () -> Matrix<T>
    const_matrix :: (a : T) -> Matrix<T>
    multiply :: (m1 : Matrix<T>, m2 : Matrix<T>) -> Matrix<T>
    transpose :: (m1 : Matrix<T>) -> Matrix<T>
    apply_scalar :: (op : (a : T, b : T) -> T, m1 : Matrix<T>, scalar : T) -> Matrix<T>
    multiply_matrix :: (op : (a : T, b : T) -> T, m1 : Matrix<T>, m2 : Matrix<T>) -> Matrix<T>
    dims :: (m1 : Matrix<T>) -> list<int>
    numdims :: (m1 : Matrix<T>) -> int
```

Now what we have is an interface for the "Matrix" type parametrized over the type of elements.  This allows us to have n-dimensional matrices (but technically it is not captured in the type itself - ie it is part of the run time interface unfortunately).   There are two things to consider here

# If we had dependent types then we could actually the make the dimensionality part of the matrix's type but we wont for now

### Types

#### Examples

##### Lists

```
record ListNode<A> {
    value : A
    next : ListNode<A>
}
```

##### Binary Trees

```
record TreeNode <A> {
    value : A
    left : TreeNode<A>
    right : TreeNode<A>
}
```

#### Builtin Types

Some times we do want built in types.  Easy way is to simply assign keywords and let the run time worry about its definitions.  But this has the down side of having to handle custom syntaxes, operations on the builtin/external type.  The advantage of this is that a lot of complexity that is not part of the core can be inserted at first as the language is fleshed out and *then* implemented locally, getting rid of the built in.

The way to however maintain this insanity is to instead of just having arbitrary functions being called, the builtin being introduced as types and type classes with their functions stipulating what is possible.  Let us go through a few examples below.

##### Arrays

While lists can be easily described easily via records above, arrays (or containers of like-entities arranged in sequantially and accessible randomly via an index) are a bit harder to describe naturally.  So this needs native support.

This can be done in two ways:

1. Treat arrays as just raw bytes in memory and nothing more
2. Treat arrays as contiguous sequence of typed entities along with bound information to prevent buffer overruns.

In Onering we go for the latter for better expressibility as well as to assist in better runtime checking.

Arrays are one such 

Grammar
-------

Here we put together the above concepts and show the formal grammar of Onering.

```
program := expr *

expr :=     literal
        |   compound_expr
        |   module_def
        |   type_def
        |   var_def
        |   fun_def
        |   "(" expr ")"

compound_expr := exprlist 
                |   list_expr
                |   tuple_expr
                |   dict_expr

exprlist := "{" ( expr ( ";" expr ) * ) ? "}"
tuple_expr := "(" expr1 , ... , exprk ")"
list_expr := "[" expr1 , ... , exprk "]"
dict_expr := "{" key_expr1 ":" value_expr1 "," ... "}"

module_def := "module" FQN "{" expr * "}"

type_def := union_def
           |    record_def
           |    enum_def
           |    alias_def

# Records
record_def := "record" type_param_decls ? FQN "{" field_decl * "}"
field_decl := ident ":" type_def ( "?" ? ) ( "=" literal ) ?

# Unions
union_def := "union" type_param_decls ? FQN "{" union_option_decl * "}"
union_option_decl := ident ":" type_def

# Enums
enum_def := "enum" FQN "{" enum_option_decl * "}"
enum_option_decl := ident ( "=" literal ) ?

# Type Aliases
alias_def := "alias" FQN type_param_decls "=" type_application

# Function definitions
fun_def := "fun" fun_sig "{" expr "}"

fun_sig := type_param_decls ? fun_name<IDENT> ? "(" fun_args ")" ( ":" fun_type_sig ) ?

fun_type_sig := type ( "->" type ) * "->" type

# Declaring type parameter lists for parametrizing a type or quantifying a function
type_param_decl := "<" type_param_decl ( "," type_param_decl ) * ">"
type_param_decl := IDENT ( ( ":" | "in" ) type_name | type_name_list )
type_name_list := "[" type_name ( "," type_name ) * "]"
type_name := IDENT
```

Lexical Structure
-----------------

The following rules describe the lexical structure of a Onering program.

### Special Characters

```
special := "()[],;:`{}"
newline := return linefeed | linefeed | return | formfeed
```

### Comments

```
// Comments can also be nested., eg:
//
// /* /* */ */
//
// is a valid comment.
comment := "/*" .* "*/" | "//.*$"
```

### Identifiers

Identifiers consiste of a letter or an underscore followed by letters, underscores or digits.

```
identifiers := [_a-zA-Z][a-zA-Z0-9_]*
```

### Fully Qualified Names (FQNs)

```
FQN := identifier ( "." identifier ) *
```

### Numeric Literals

```
numeric := int_numeric | double_numeric | boolean_numeric
```

### String Literals

```
string_lit := quote [^<newline>]* quote
        | triple_quote .* triple_quote
```


### Miscellaneous and Future Work

#### Operatorless

```
operator := operator_symbol +

operator_symbol := [@#$%^&*!-+=|?<>]
```

Onering is high level language and does not want to get into the business of fancy operators.  So operators are to be created very very judiciously.  For now operators are not for users and they are only used by the parser.  This will be opened up more as the usefulness and flexibility (for both good and evil) is analyzed a bit more.
