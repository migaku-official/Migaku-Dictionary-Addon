function insertHTML(newHTML, ord, action) {
  const field = document.getElementById("f" + ord)
  if(action == "overwrite"){
  	field.innerHTML = newHTML;
  }else if(action == "add"){
  	if(field.innerHTML === "<br>") {
  		field.innerHTML = newHTML;
  	}else{
  		field.innerHTML = field.innerHTML + "<br><br>" + newHTML;
  	}
  }else if(action == "no"){
  	if(field.innerHTML === "<br>") {
  		field.innerHTML = newHTML;
  	}
  }
  pycmd("key" + ":" + parseInt(ord) + ":" + currentNoteId + ":" + field.innerHTML);
  // setFormat("inserthtml", field.innerHTML);
  // setFormat("inserthtml", newHTML.trim());

}
try {

  insertHTML("%s", "%s", "%s");
} catch (e) {
  alert(e);
}
