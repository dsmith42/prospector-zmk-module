zephyr_include_directories(include)
zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)
zephyr_library()

# Focus-block timer: state, event and behaviour are display-agnostic and must
# build on every target, because split peripherals compile the same keymap and
# have to resolve the binding. Only the widget is shield-specific.
zephyr_library_sources(src/block_timer.c)
zephyr_library_sources(src/events/block_timer_state_changed.c)

if(CONFIG_DT_HAS_ZMK_BEHAVIOR_BLOCK_TIMER_ENABLED)
        zephyr_library_sources(src/behaviors/behavior_block_timer.c)
endif()

if(CONFIG_SHIELD_PROSPECTOR_ADAPTER)

        add_subdirectory(${ZEPHYR_CURRENT_MODULE_DIR}/drivers/display)

        if(CONFIG_DT_HAS_ZMK_BEHAVIOR_CAPS_WORD_ENABLED)
                zephyr_library_sources(src/events/caps_word_state_changed.c)
                set_source_files_properties(
                        ${APPLICATION_SOURCE_DIR}/src/behaviors/behavior_caps_word.c
                        TARGET_DIRECTORY app
                        PROPERTIES HEADER_FILE_ONLY ON)
                target_sources(app PRIVATE src/behaviors/behavior_caps_word.c)
        endif()

        zephyr_library_sources(src/events/split_central_status_changed.c)
        zephyr_library_sources(src/split/bluetooth/central_status_changed_observer.c)

endif()