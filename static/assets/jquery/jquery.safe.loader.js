console.log("loading jquery...");
console.log(window.jQuery);
if(typeof jQuery == "undefined") {
    document.write('<script type="text/javascript" src="/static/jquery3/jquery.js"></script>');
}else{
    console.log("jquery already loaded...");
}
