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
