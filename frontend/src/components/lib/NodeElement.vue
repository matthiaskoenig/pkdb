<template>
    <span>
      <strong>
        <text-highlight :queries="highlight">
        {{ data.label }}
        </text-highlight>
        </strong>
    </span>
</template>

<script>
    export default {
        name: "NodeElement",
        components: {

        },
        props: {
            data: {
                type: Object,
                required: true
            }
        },
        computed: {
            highlight(){
              return this.$store.state.highlight
            },
        },
        methods: {
        }
    }

</script>

<style scoped>

</style>