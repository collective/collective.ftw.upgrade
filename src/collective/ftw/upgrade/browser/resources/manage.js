$(document).ready(function() {
    $('.select-none').click(function(e) {
        e.preventDefault();
        $('.profiles input[type=checkbox]').prop('checked', false);
    });

    $('.select-not-installed').click(function(e) {
        e.preventDefault();
        $('.profiles input[type=checkbox]').prop('checked', false);
        $('.profiles .upgrade.proposed input[type=checkbox]').prop('checked', true);
    });

    $('.profiles .profile-title strong').click(function(e){
        e.preventDefault();
        var profile = $(this).parents('.profile:first');
        var to_visible = profile.hasClass('hide-done');
        profile.toggleClass('hide-done');
        profile.find('.upgrade.done').each(function() {
            if(to_visible) {
                $(this).show();
            } else if(!$(this).find('input[type=checkbox]').attr('checked')) {
                $(this).hide();
            }
        });
    });

    $('.profiles .upgrade').click(function(e) {
        if($(e.target).is('input[type=checkbox]')) {
            return;
        }
        var checkbox = $('input[type=checkbox]', $(this));
        checkbox.prop('checked', !checkbox.prop('checked'));
    });

    $('#upgrade-form').submit(function(e) {
        e.preventDefault();
        var $form = $(this);
        $form.hide();
        $('#upgrade-progress').show();

        $.ajax({
            url: $form.attr('action'),
            type: 'POST',
            data: $form.serialize(),
            dataType: 'text',
            success: function(data) {
                $('#upgrade-progress').hide();
                $('#upgrade-log').text(data);
                $('#upgrade-output').show();
                $('#back-to-upgrades').show();
            },
            error: function(xhr) {
                $('#upgrade-progress').hide();
                $('#upgrade-log').text(
                    'Error during upgrade execution:\n' +
                    (xhr.responseText || 'Unknown error')
                );
                $('#upgrade-output').show();
                $('#back-to-upgrades').show();
            }
        });
    });

    $('#back-to-upgrades').click(function(e) {
        location.reload();
    });

    $('[data-human-readable-version]').each(function() {
        $(this).data('original-version', $(this).text());
        $(this).text($(this).data('human-readable-version'));
    }).on('mouseenter', function(event) {
        $(this).text($(this).data('original-version'));
    }).on('mouseleave', function(event) {
        $(this).text($(this).data('human-readable-version'));
    });
});
