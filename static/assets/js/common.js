$(document).ready(function () {

  // Toggle dropdown
$(document).on('click', '[data-dropdown]', function (e) {
    e.stopPropagation();

    const key = $(this).data('dropdown');
    const $menu = $(`[data-dropdown-menu="${key}"]`);

    // Close all others
    $('[data-dropdown-menu]').not($menu).addClass('hidden');

    // Toggle current
    $menu.toggleClass('hidden');
});

// Click inside dropdown should NOT close it
$(document).on('click', '[data-dropdown-menu]', function (e) {
    e.stopPropagation();
});

// Click outside → close all
$(document).on('click', function () {
    $('[data-dropdown-menu]').addClass('hidden');
});



});
