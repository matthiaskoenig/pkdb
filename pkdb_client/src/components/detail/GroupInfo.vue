<template>
    <span class="group-info">
        <span class="attr-card">
            <v-btn small color="black" fab dark title="Group Size">{{ group.count }}</v-btn><br/>
        </span>
        <!--
        <div class="attr-card" v-if="(group.individuals && group.individuals.length>0)">
            <span class="attr"></span><br />
            <v-icon>fa fa-check-circle</v-icon> {{ group.individuals.length }} Individuals
        </div>
        -->
    </span>
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