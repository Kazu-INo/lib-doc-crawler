
---
source: https://docs.pola.rs/
crawled_at: 2024-12-21 06:59:04
---

Blazingly Fast DataFrame Library
Polars is a blazingly fast DataFrame library for manipulating structured data. The core is written in Rust, and available for Python, R and NodeJS.
Key features
- Fast: Written from scratch in Rust, designed close to the machine and without external dependencies.
- I/O: First class support for all common data storage layers: local, cloud storage & databases.
- Intuitive API: Write your queries the way they were intended. Polars, internally, will determine the most efficient way to execute using its query optimizer.
- Out of Core: The streaming API allows you to process your results without requiring all your data to be in memory at the same time.
- Parallel: Utilises the power of your machine by dividing the workload among the available CPU cores without any additional configuration.
- Vectorized Query Engine: Using Apache Arrow, a columnar data format, to process your queries in a vectorized manner and SIMD to optimize CPU usage.
- GPU Support: Optionally run queries on NVIDIA GPUs for maximum performance for in-memory workloads.
Users new to DataFrames
A DataFrame is a 2-dimensional data structure that is useful for data manipulation and analysis. With labeled axes for rows and columns, each column can contain different data types, making complex data operations such as merging and aggregation much easier. Due to their flexibility and intuitive way of storing and working with data, DataFrames have become increasingly popular in modern data analytics and engineering.
Philosophy
The goal of Polars is to provide a lightning fast DataFrame library that:
- Utilizes all available cores on your machine.
- Optimizes queries to reduce unneeded work/memory allocations.
- Handles datasets much larger than your available RAM.
- A consistent and predictable API.
- Adheres to a strict schema (data-types should be known before running the query).
Polars is written in Rust which gives it C/C++ performance and allows it to fully control performance-critical parts in a query engine.
Example
scan_csv
· filter
· group_by
· collect
import polars as pl
q = (
pl.scan_csv("docs/assets/data/iris.csv")
.filter(pl.col("sepal_length") > 5)
.group_by("species")
.agg(pl.all().sum())
)
df = q.collect()
LazyCsvReader
· filter
· group_by
· collect
· Available on feature streaming · Available on feature csv
use polars::prelude::*;
let q = LazyCsvReader::new("docs/assets/data/iris.csv")
.with_has_header(true)
.finish()?
.filter(col("sepal_length").gt(lit(5)))
.group_by(vec![col("species")])
.agg([col("*").sum()]);
let df = q.collect()?;
A more extensive introduction can be found in the next chapter.
Community
Polars has a very active community with frequent releases (approximately weekly). Below are some of the top contributors to the project:
Contributing
We appreciate all contributions, from reporting bugs to implementing new features. Read our contributing guide to learn more.
License
This project is licensed under the terms of the MIT license.

---

---
source: https://docs.pola.rs/user-guide/plugins/your-first-polars-plugin/
crawled_at: 2024-12-21 06:59:06
---

Your first Polars plugin
Expression plugins are the preferred way to create user defined functions. They allow you to compile a Rust function and register that as an expression into the Polars library. The Polars engine will dynamically link your function at runtime and your expression will run almost as fast as native expressions. Note that this works without any interference of Python and thus no GIL contention.
They will benefit from the same benefits default expressions have:
- Optimization
- Parallelism
- Rust native performance
To get started we will see what is needed to create a custom expression.
Our first custom expression: Pig Latin
For our first expression we are going to create a pig latin converter. Pig latin is a silly language where in every word the first letter is removed, added to the back and finally "ay" is added. So the word "pig" would convert to "igpay".
We could of course already do that with expressions, e.g.
col("name").str.slice(1) + col("name").str.slice(0, 1) + "ay"
, but a specialized function for this
would perform better and allows us to learn about the plugins.
Setting up
We start with a new library as the following Cargo.toml
file
[package]
name = "expression_lib"
version = "0.1.0"
edition = "2021"
[lib]
name = "expression_lib"
crate-type = ["cdylib"]
[dependencies]
polars = { version = "*" }
pyo3 = { version = "*", features = ["extension-module", "abi3-py38"] }
pyo3-polars = { version = "*", features = ["derive"] }
serde = { version = "*", features = ["derive"] }
Writing the expression
In this library we create a helper function that converts a &str
to pig-latin, and we create the
function that we will expose as an expression. To expose a function we must add the
#[polars_expr(output_type=DataType)]
attribute and the function must always accept
inputs: &[Series]
as its first argument.
// src/expressions.rs
use polars::prelude::*;
use pyo3_polars::derive::polars_expr;
use std::fmt::Write;
fn pig_latin_str(value: &str, output: &mut String) {
if let Some(first_char) = value.chars().next() {
write!(output, "{}{}ay", &value[1..], first_char).unwrap()
}
}
#[polars_expr(output_type=String)]
fn pig_latinnify(inputs: &[Series]) -> PolarsResult<Series> {
let ca = inputs[0].str()?;
let out: StringChunked = ca.apply_into_string_amortized(pig_latin_str);
Ok(out.into_series())
}
Note that we use apply_into_string_amortized
, as opposed to apply_values
, to avoid allocating a
new string for each row. If your plugin takes in multiple inputs, operates elementwise, and produces
a String
output, then you may want to look at the binary_elementwise_into_string_amortized
utility function in polars::prelude::arity
.
This is all that is needed on the Rust side. On the Python side we must setup a folder with the same
name as defined in the Cargo.toml
, in this case "expression_lib". We will create a folder in the
same directory as our Rust src
folder named expression_lib
and we create an
expression_lib/__init__.py
. The resulting file structure should look something like this:
├── 📁 expression_lib/ # name must match "lib.name" in Cargo.toml
| └── __init__.py
|
├── 📁src/
| ├── lib.rs
| └── expressions.rs
|
├── Cargo.toml
└── pyproject.toml
Then we create a new class Language
that will hold the expressions for our new expr.language
namespace. The function name of our expression can be registered. Note that it is important that
this name is correct, otherwise the main Polars package cannot resolve the function name.
Furthermore we can set additional keyword arguments that explain to Polars how this expression
behaves. In this case we tell Polars that this function is elementwise. This allows Polars to run
this expression in batches. Whereas for other operations this would not be allowed, think for
instance of a sort, or a slice.
# expression_lib/__init__.py
from pathlib import Path
from typing import TYPE_CHECKING
import polars as pl
from polars.plugins import register_plugin_function
from polars._typing import IntoExpr
PLUGIN_PATH = Path(__file__).parent
def pig_latinnify(expr: IntoExpr) -> pl.Expr:
"""Pig-latinnify expression."""
return register_plugin_function(
plugin_path=PLUGIN_PATH,
function_name="pig_latinnify",
args=expr,
is_elementwise=True,
)
We can then compile this library in our environment by installing maturin
and running
maturin develop --release
.
And that's it. Our expression is ready to use!
import polars as pl
from expression_lib import pig_latinnify
df = pl.DataFrame(
{
"convert": ["pig", "latin", "is", "silly"],
}
)
out = df.with_columns(pig_latin=pig_latinnify("convert"))
Alternatively, you can register a custom namespace, which enables you to write:
out = df.with_columns(
pig_latin=pl.col("convert").language.pig_latinnify(),
)
Accepting kwargs
If you want to accept kwargs
(keyword arguments) in a polars expression, all you have to do is
define a Rust struct
and make sure that it derives serde::Deserialize
.
/// Provide your own kwargs struct with the proper schema and accept that type
/// in your plugin expression.
#[derive(Deserialize)]
pub struct MyKwargs {
float_arg: f64,
integer_arg: i64,
string_arg: String,
boolean_arg: bool,
}
/// If you want to accept `kwargs`. You define a `kwargs` argument
/// on the second position in you plugin. You can provide any custom struct that is deserializable
/// with the pickle protocol (on the Rust side).
#[polars_expr(output_type=String)]
fn append_kwargs(input: &[Series], kwargs: MyKwargs) -> PolarsResult<Series> {
let input = &input[0];
let input = input.cast(&DataType::String)?;
let ca = input.str().unwrap();
Ok(ca
.apply_into_string_amortized(|val, buf| {
write!(
buf,
"{}-{}-{}-{}-{}",
val, kwargs.float_arg, kwargs.integer_arg, kwargs.string_arg, kwargs.boolean_arg
)
.unwrap()
})
.into_series())
}
On the Python side the kwargs can be passed when we register the plugin.
def append_args(
expr: IntoExpr,
float_arg: float,
integer_arg: int,
string_arg: str,
boolean_arg: bool,
) -> pl.Expr:
"""
This example shows how arguments other than `Series` can be used.
"""
return register_plugin_function(
plugin_path=PLUGIN_PATH,
function_name="append_kwargs",
args=expr,
kwargs={
"float_arg": float_arg,
"integer_arg": integer_arg,
"string_arg": string_arg,
"boolean_arg": boolean_arg,
},
is_elementwise=True,
)
Output data types
Output data types of course don't have to be fixed. They often depend on the input types of an
expression. To accommodate this you can provide the #[polars_expr()]
macro with an
output_type_func
argument that points to a function. This function can map input fields &[Field]
to an output Field
(name and data type).
In the snippet below is an example where we use the utility FieldsMapper
to help with this
mapping.
use polars_plan::dsl::FieldsMapper;
fn haversine_output(input_fields: &[Field]) -> PolarsResult<Field> {
FieldsMapper::new(input_fields).map_to_float_dtype()
}
#[polars_expr(output_type_func=haversine_output)]
fn haversine(inputs: &[Series]) -> PolarsResult<Series> {
let out = match inputs[0].dtype() {
DataType::Float32 => {
let start_lat = inputs[0].f32().unwrap();
let start_long = inputs[1].f32().unwrap();
let end_lat = inputs[2].f32().unwrap();
let end_long = inputs[3].f32().unwrap();
crate::distances::naive_haversine(start_lat, start_long, end_lat, end_long)?
.into_series()
}
DataType::Float64 => {
let start_lat = inputs[0].f64().unwrap();
let start_long = inputs[1].f64().unwrap();
let end_lat = inputs[2].f64().unwrap();
let end_long = inputs[3].f64().unwrap();
crate::distances::naive_haversine(start_lat, start_long, end_lat, end_long)?
.into_series()
}
_ => polars_bail!(InvalidOperation: "only supported for float types"),
};
Ok(out)
}
That's all you need to know to get started. Take a look at this repo to see how this all fits together, and at this tutorial to gain a more thorough understanding.
Community plugins
Here is a curated (non-exhaustive) list of community-implemented plugins.
- polars-xdt Polars plugin with extra datetime-related functionality which isn't quite in-scope for the main library
- polars-distance Polars plugin for pairwise distance functions
- polars-ds Polars extension aiming to simplify common numerical/string data analysis procedures
- polars-hash Stable non-cryptographic and cryptographic hashing functions for Polars
- polars-reverse-geocode Offline reverse geocoder for finding the closest city to a given (latitude, longitude) pair
Other material
- Ritchie Vink - Keynote on Polars Plugins
- Polars plugins tutorial Learn how to write a plugin by going through some very simple and minimal examples
- cookiecutter-polars-plugin Project template for Polars Plugins

---