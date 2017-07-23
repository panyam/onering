var onering = (exports.onering = {});
onering.core = {};
onering.core.externs = {};

onering.core.externs.dict_get = function(dict, key) {
    return dict[key];
};

onering.core.externs.dict_put = function(dict, key, value) {
    dict[key] = value;
    return dict;
};

onering.core.externs.decode_json = function(buffer) {
  var buffstr = buffer.toString();
  try {
        return JSON.parse(buffstr);
  } catch (e) {
      console.log("JSON Parse Error: ", e);
      return buffstr;
  }
};

onering.core.externs.concat = function(items) {
    return items.join("");
};

onering.core.externs.ensure_field_path = function (starting_var, typeinfo, field_path) {
    field_path = field_path .filter(function(x) { return x.trim().length > 0; });
    var a = 0;
    null.a = 3;
};

onering.core.externs.get_field_path = function (starting_var, typeinfo, field_path) {
    field_path = field_path .filter(function(x) { return x.trim().length > 0; });
    if (field_path.length == 0) {
        return starting_var;
    }

    // otherwise keep diving in
    null.a = 3;
};
