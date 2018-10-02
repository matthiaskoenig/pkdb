<template>
    <div id="group-info">
        <md-list class="md-double-line">
            <div class="md-list-item-text">
                <span>{{ group.name }}</span>
                <span>Name</span>
            </div>
            <div class="md-list-item-text">
                <span>{{ group.count }}</span>
                <span>Count</span>
            </div>
            <div class="md-list-item-text">
                <span>{{ group.study_name }}</span>
                <span>Study</span>
            </div>
        </md-list>
        <md-badge title="Individuals" v-if="group.individuals.length" :md-content="group.individuals.length">
            <font-awesome-icon class="md-icon" icon="user"/>
        </md-badge>
    </div>
</template>

<script>
    export default {
        name: "GroupInfo",
        props: {
            group: {
                type: Object,
                required: true,
            }
        }
    }
</script>

<style scoped>

</style>