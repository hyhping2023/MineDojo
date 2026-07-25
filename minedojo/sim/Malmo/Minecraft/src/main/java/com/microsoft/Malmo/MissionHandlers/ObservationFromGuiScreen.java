// --------------------------------------------------------------------------------------------------
//  Copyright (c) 2016 Microsoft Corporation
//  
//  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
//  associated documentation files (the "Software"), to deal in the Software without restriction,
//  including without limitation the rights to use, copy, modify, merge, publish, distribute,
//  sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
//  furnished to do so, subject to the following conditions:
//  
//  The above copyright notice and this permission notice shall be included in all copies or
//  substantial portions of the Software.
//  
//  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
//  NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
//  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
//  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// --------------------------------------------------------------------------------------------------

package com.microsoft.Malmo.MissionHandlers;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import com.microsoft.Malmo.MissionHandlerInterfaces.IObservationProducer;
import com.microsoft.Malmo.Schemas.MissionInit;

import net.minecraft.client.Minecraft;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.ContainerBrewingStand;
import net.minecraft.inventory.ContainerChest;
import net.minecraft.inventory.ContainerEnchantment;
import net.minecraft.inventory.ContainerFurnace;
import net.minecraft.inventory.ContainerHopper;
import net.minecraft.inventory.ContainerMerchant;
import net.minecraft.inventory.ContainerPlayer;
import net.minecraft.inventory.ContainerRepair;
import net.minecraft.inventory.ContainerWorkbench;
import net.minecraft.inventory.IInventory;
import net.minecraft.inventory.Slot;
import net.minecraft.item.ItemStack;

/**
 * Observation producer that reports the current GUI screen state.
 * Reports current_gui (string) and gui_slots (list of items per slot for container GUIs).
 */
public class ObservationFromGuiScreen extends HandlerBase implements IObservationProducer
{
    @Override
    public void prepare(MissionInit missionInit)
    {
    }

    @Override
    public void cleanup()
    {
    }

    private String getGuiType(Container container)
    {
        if (container == null || container instanceof ContainerPlayer)
            return "none";
        if (container instanceof ContainerMerchant)
            return "trade";
        if (container instanceof ContainerEnchantment)
            return "enchant";
        if (container instanceof ContainerBrewingStand)
            return "brewing";
        if (container instanceof ContainerRepair)
            return "anvil";
        if (container instanceof ContainerWorkbench)
            return "crafting";
        if (container instanceof ContainerChest || container instanceof ContainerFurnace
            || container instanceof ContainerHopper)
            return "chest";
        return "none";
    }

    private JsonArray getGuiSlots(Container container)
    {
        JsonArray slots = new JsonArray();
        if (container == null)
            return slots;

        for (int i = 0; i < container.inventorySlots.size(); i++)
        {
            Slot slot = container.inventorySlots.get(i);
            if (slot == null)
                continue;

            ItemStack stack = slot.getStack();
            JsonObject slotEntry = new JsonObject();
            slotEntry.addProperty("slot_index", i);

            if (stack != null && !stack.isEmpty())
            {
                slotEntry.addProperty("item_type",
                    stack.getItem().getRegistryName() != null
                        ? stack.getItem().getRegistryName().toString()
                        : "unknown");
                slotEntry.addProperty("item_metadata", stack.getMetadata());
                slotEntry.addProperty("item_count", stack.getCount());
            }
            else
            {
                slotEntry.addProperty("item_type", "empty");
                slotEntry.addProperty("item_metadata", 0);
                slotEntry.addProperty("item_count", 0);
            }
            slots.add(slotEntry);
        }
        return slots;
    }

    @Override
    public void writeObservationsToJSON(JsonObject json, MissionInit missionInit)
    {
        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null || mc.player == null)
        {
            json.addProperty("current_gui", "none");
            json.add("gui_slots", new JsonArray());
            return;
        }

        Container openContainer = mc.player.openContainer;
        String guiType = getGuiType(openContainer);
        json.addProperty("current_gui", guiType);

        // Only report slots for container-based GUIs (not inventory)
        if (!guiType.equals("none"))
        {
            json.add("gui_slots", getGuiSlots(openContainer));
        }
        else
        {
            json.add("gui_slots", new JsonArray());
        }
    }
}
