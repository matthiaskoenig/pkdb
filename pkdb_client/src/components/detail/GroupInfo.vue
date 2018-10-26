<template>
    <div class="group-info">
        <!--
        <div class="group-card">
            <v-icon color="primary">{{ icon('group') }}</v-icon>
        </div>
        -->
        <div class="attr-card">
            <v-btn small color="black" fab dark title="Group Size">{{ group.count }}</v-btn><br/>

            <span class="attr" title="Group Name">{{ group.name }}</span><br />
        </div>
        <div class="attr-card">
            <span v-if="(group.individuals && group.individuals.length>0)">
                <span class="attr"></span><br />
                <v-icon>fa fa-check-circle</v-icon> {{ group.individuals.length }} Individuals
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