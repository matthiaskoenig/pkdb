<template>
    <div class="group-info">
        <!--
        <div class="group-card">
            <v-icon color="primary">{{ icon('group') }}</v-icon>
        </div>
        -->
        <div class="attr-card">
            <span class="attr">Group Name</span><br />
            {{ group.name }}
        </div>
        <div class="attr-card">
            <span class="attr">Group Size</span><br />
            <v-btn small color="black" fab dark>{{ group.count }}</v-btn>

        </div>
        <div class="attr-card">
            <span class="attr">Individuals</span><br />
            <span v-if="(group.individuals && group.individuals.length>0)">
            <v-icon>fa fa-check-circle</v-icon> {{ group.individuals.length }}</span>
            <span v-else>
            <v-icon>fa fa-times-circle</v-icon>
        </span>
        </div>
    </div>
</template>

<script>
    import {lookup_icon} from "@/icons"
    export default {
        name: "GroupInfo",
        props: {
            group: {
                type: Object,
                required: true,
            }
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },

        }
    }
</script>

<style scoped>

</style>