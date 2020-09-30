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
    import {StoreInteractionMixin} from "../../storeInteraction";

    export default {
        name: "NodeElement",
      mixins: [StoreInteractionMixin],
      components: {

        },
        props: {
            data: {
                type: Object,
                required: true
            }
        }

    }

</script>

<style scoped>

</style>